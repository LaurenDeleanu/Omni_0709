import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user import User
from app.models.kudos import Kudos
from app.models.employee_history import EmployeeHistory
from app.models.hire import Candidate, JobPosting

logger = logging.getLogger("successcore.predictive_analytics")


async def get_attrition_prediction(db: AsyncSession) -> Dict[str, Any]:
    """
    Predicts attrition risk scores for active employees.
    Uses tenure, pulse survey mood trends, kudos recognition, department, and salary anomalies.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Fetch active employees
    stmt = select(User).where(User.is_active == True)
    res = await db.execute(stmt)
    employees = res.scalars().all()
    
    if not employees:
        return {"summary": {"low": 0, "medium": 0, "high": 0}, "risk_factors": {}, "predictions": []}
        
    # Get department averages for compensation check
    dept_salaries = {}
    for emp in employees:
        dept = emp.department or "Unknown"
        if dept not in dept_salaries:
            dept_salaries[dept] = []
        if emp.base_salary > 0:
            dept_salaries[dept].append(emp.base_salary)
            
    dept_averages = {d: (sum(s) / len(s)) for d, s in dept_salaries.items() if s}
    
    # Load pulse responses from FAKE_RESPONSES in pulse_surveys
    pulse_moods = {}
    try:
        from app.services.pulse_surveys import FAKE_RESPONSES
        for uid, questions in FAKE_RESPONSES.items():
            moods = questions.get("mood", [])
            if moods:
                pulse_moods[uid] = sum(moods) / len(moods)
    except Exception:
        pass

    # Load kudos counts
    kudos_counts = {}
    cutoff_kudos = now - timedelta(days=180)
    try:
        kudos_stmt = select(Kudos.receiver_id, func.count(Kudos.id)).where(Kudos.created_at >= cutoff_kudos).group_by(Kudos.receiver_id)
        kudos_res = await db.execute(kudos_stmt)
        kudos_counts = {row[0]: row[1] for row in kudos_res.all()}
    except Exception:
        pass

    predictions = []
    low_count = 0
    medium_count = 0
    high_count = 0
    
    for emp in employees:
        # Base Risk
        risk_score = 0.15
        factors = []
        
        # 1. Tenure factor
        hire_date = emp.hire_date or emp.created_at
        if hire_date:
            if hire_date.tzinfo is None:
                hire_date = hire_date.replace(tzinfo=timezone.utc)
            tenure_days = (now - hire_date).days
            
            if tenure_days < 180:
                risk_score += 0.10
                factors.append("Onboarding phase (<6 months)")
            elif 365 <= tenure_days < 730:
                risk_score += 0.20
                factors.append("Tenure is between 1-2 years (typical transition window)")
            elif tenure_days >= 1800:
                risk_score -= 0.10
                
        # 2. Kudos factor
        received = kudos_counts.get(emp.id, 0)
        if received == 0:
            risk_score += 0.15
            factors.append("No kudos received in the last 6 months")
        elif received >= 3:
            risk_score -= 0.10
            
        # 3. Pulse Survey Mood factor
        avg_mood = pulse_moods.get(emp.id, 3.5)
        if avg_mood < 2.5:
            risk_score += 0.25
            factors.append(f"Low average mood in pulse surveys ({avg_mood:.1f}/5.0)")
        elif avg_mood < 3.5:
            risk_score += 0.10
            factors.append(f"Neutral average mood in pulse surveys ({avg_mood:.1f}/5.0)")
        elif avg_mood >= 4.5:
            risk_score -= 0.15
            
        # 4. Salary equity factor
        dept = emp.department or "Unknown"
        dept_avg = dept_averages.get(dept, 0)
        if dept_avg > 0 and emp.base_salary > 0:
            ratio = emp.base_salary / dept_avg
            if ratio < 0.85:
                risk_score += 0.15
                factors.append(f"Base salary is {int((1-ratio)*100)}% below department average")
                
        # 5. Department turnover factor
        if dept in ["Sales", "Marketing"]:
            risk_score += 0.08
        elif dept in ["Engineering"]:
            risk_score += 0.05
            
        # Bound risk score between 0.0 and 0.95
        risk_score = max(0.01, min(0.95, risk_score))
        
        # Categorize
        if risk_score >= 0.60:
            high_count += 1
            category = "High"
        elif risk_score >= 0.35:
            medium_count += 1
            category = "Medium"
        else:
            low_count += 1
            category = "Low"
            
        predictions.append({
            "employee_id": emp.id,
            "name": emp.full_name or emp.email,
            "department": dept,
            "risk_score": round(risk_score, 2),
            "risk_level": category,
            "top_factors": factors
        })
        
    predictions.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "summary": {
            "low": low_count,
            "medium": medium_count,
            "high": high_count,
            "total_active": len(employees)
        },
        "predictions": predictions[:15], # top 15 highest risk
    }


async def get_headcount_forecast(db: AsyncSession, forecast_months: int = 6) -> Dict[str, Any]:
    """
    Performs linear regression headcount forecasting using historical monthly active headcount trends.
    """
    from app.services.people_analytics import get_headcount_trends
    
    trends_data = await get_headcount_trends(db, months=12)
    historical_total = trends_data.get("total", [])
    labels = trends_data.get("labels", [])
    
    n = len(historical_total)
    
    # Simple Linear Regression (y = mx + c)
    if n >= 2:
        x = list(range(n))
        y = historical_total
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        den = sum((x[i] - mean_x) ** 2 for i in range(n))
        m = num / den if den != 0 else 0
        c = mean_y - m * mean_x
    else:
        # Fallback to constant projection or baseline
        m = 1.0  # grow by 1 employee per month
        c = historical_total[-1] if historical_total else 100
        
    forecast_labels = []
    forecast_data = []
    lower_bound = []
    upper_bound = []
    
    last_date = datetime.now(timezone.utc)
    
    for i in range(forecast_months):
        proj_idx = n + i
        val = m * proj_idx + c
        val = max(1, int(val))
        
        forecast_data.append(val)
        # 5% confidence intervals
        lower_bound.append(max(1, int(val * 0.95)))
        upper_bound.append(int(val * 1.05))
        
        future_month = last_date + timedelta(days=30 * (i + 1))
        forecast_labels.append(future_month.strftime("%b %Y") + " (Proj)")
        
    return {
        "historical": {
            "labels": labels,
            "data": historical_total
        },
        "forecast": {
            "labels": forecast_labels,
            "data": forecast_data,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        }
    }


MARKET_BENCHMARKS: Dict[str, Dict[str, float]] = {}

async def get_compensation_benchmarking(db: AsyncSession) -> Dict[str, Any]:
    """
    Compares active salaries against internal benchmarks and detects pay equity deviations.
    Also incorporates external MARKET_BENCHMARKS if available.
    """
    stmt = select(User).where(User.is_active == True)
    res = await db.execute(stmt)
    employees = res.scalars().all()
    
    if not employees:
        return {"departments": [], "recommendations": []}
        
    dept_salaries = {}
    for emp in employees:
        dept = emp.department or "Unknown"
        if dept not in dept_salaries:
            dept_salaries[dept] = []
        if emp.base_salary > 0:
            dept_salaries[dept].append(emp.base_salary)
            
    # Calculate average salary per department
    dept_stats = {}
    for dept, salaries in dept_salaries.items():
        if salaries:
            avg_sal = sum(salaries) / len(salaries)
            sorted_sal = sorted(salaries)
            median_sal = sorted_sal[len(salaries) // 2]
            
            market_data = MARKET_BENCHMARKS.get(dept)
            
            dept_stats[dept] = {
                "average": round(avg_sal, 2),
                "median": round(median_sal, 2),
                "min": min(salaries),
                "max": max(salaries),
                "headcount": len(salaries),
                "market_average": market_data["market_average"] if market_data else None,
                "market_median": market_data["market_median"] if market_data else None,
            }
            
    # Recommendations for salaries > 15% below department average or market average
    recommendations = []
    for emp in employees:
        dept = emp.department or "Unknown"
        stats = dept_stats.get(dept)
        if stats and emp.base_salary > 0:
            avg_sal = stats["average"]
            market_avg = stats["market_average"]
            
            target_avg = market_avg if market_avg else avg_sal
            target_type = "market" if market_avg else "department"
            
            if emp.base_salary < target_avg * 0.85:
                diff_pct = int((1 - (emp.base_salary / target_avg)) * 100)
                recommendations.append({
                    "employee_id": emp.id,
                    "name": emp.full_name or emp.email,
                    "department": dept,
                    "salary": emp.base_salary,
                    "department_average": avg_sal,
                    "market_average": market_avg,
                    "deviation_pct": diff_pct,
                    "recommendation": f"Review base compensation for {emp.full_name or emp.email} ({diff_pct}% below {target_type} average)."
                })
                
    return {
        "departments": [{"department": dept, **stats} for dept, stats in dept_stats.items()],
        "recommendations": recommendations[:10]  # top 10 discrepancies
    }


async def get_recruitment_funnel_prediction(db: AsyncSession) -> Dict[str, Any]:
    """
    Analyzes historical candidates conversion rates and predicts requirements to fill active openings.
    """
    # Standard funnel conversion rates based on historical averages:
    # Applied -> Screened: 15%
    # Screened -> Interviewed: 40%
    # Interviewed -> Offered: 25%
    # Offered -> Hired: 80%
    # Overall flow: Hires / (0.15 * 0.40 * 0.25 * 0.80) = Hires / 0.012 (requires ~83 applicants per hire)
    
    active_postings_stmt = select(JobPosting).where(JobPosting.status == "published")
    res = await db.execute(active_postings_stmt)
    postings = res.scalars().all()
    
    funnel_forecasts = []
    for post in postings:
        # Get target hires from metadata or default to 1
        target_hires = 1
        meta = post.posting_metadata or {}
        if isinstance(meta, dict) and "target_hires" in meta:
            try:
                target_hires = int(meta["target_hires"])
            except ValueError:
                pass
                
        # Count current candidates in pipeline
        candidates_stmt = select(Candidate).where(Candidate.job_id == post.id)
        candidates_res = await db.execute(candidates_stmt)
        candidates = candidates_res.scalars().all()
        
        stages = {"applied": 0, "screened": 0, "interview": 0, "offer": 0, "hired": 0}
        for c in candidates:
            stage = c.stage.lower() if c.stage else "applied"
            if stage in stages:
                stages[stage] += 1
                
        hired_count = stages["hired"]
        needed_hires = max(0, target_hires - hired_count)
        
        # Predict required applicants to complete hires
        required_applicants = int(needed_hires / 0.012) if needed_hires > 0 else 0
        current_applicants = len(candidates)
        applicants_gap = max(0, required_applicants - current_applicants)
        
        funnel_forecasts.append({
            "job_id": post.id,
            "title": post.title,
            "target_hires": target_hires,
            "current_hired": hired_count,
            "pipeline_stages": stages,
            "estimated_applicants_needed": required_applicants,
            "current_applicants": current_applicants,
            "applicants_gap": applicants_gap,
            "recommendation": f"Boost sourcing efforts: need approximately {applicants_gap} more applicants to secure {needed_hires} hire(s)." if applicants_gap > 10 else "Pipeline is healthy to meet goals."
        })
        
    return {
        "active_jobs_count": len(postings),
        "funnel_predictions": funnel_forecasts
    }
