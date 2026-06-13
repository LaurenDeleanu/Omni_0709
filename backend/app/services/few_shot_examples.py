"""
Phase 3/4: 50 Few-Shot Training Examples for agent system prompts.
5 examples each for 10 agent types, used to improve agent accuracy.
"""

import logging
from typing import Dict, List

logger = logging.getLogger("successcore.few_shot")

FEW_SHOT_EXAMPLES: Dict[str, List[Dict]] = {
    # ── HR Assistant (5 examples) ──────────────────────────────────────────
    "hr_assistant": [
        {
            "user": "Show me Jane's PTO balance",
            "assistant": "Let me look up Jane Smith's PTO balance in the system.",
            "tool_calls": [{"tool": "get_pto_balance", "args": {"employee_id": "emp-8a3f-4b2c"}}],
            "tool_results": [{"employee": "Jane Smith", "remaining": 15, "used": 7, "allowance": 22}],
            "final_response": "Jane Smith has 15 remaining vacation days out of 22 for this year. She has used 7 days so far. Her next planned absence is June 15-18."
        },
        {
            "user": "Who reports to the CTO?",
            "assistant": "I'll retrieve the org chart for the CTO position.",
            "tool_calls": [{"tool": "get_org_chart", "args": {"position": "CTO"}}],
            "tool_results": [{"cto": "Marcus Rivera", "direct_reports": ["Head of Platform", "Head of Data", "VP Infrastructure", "Director of Security"]}],
            "final_response": "Marcus Rivera is the CTO. Four leaders report directly to him: the Head of Platform (Sofia Chen), Head of Data (David Park), VP Infrastructure (Ana Torres), and Director of Security (Raj Patel)."
        },
        {
            "user": "Show me the Engineering org chart",
            "assistant": "Retrieving the organizational chart for the Engineering department.",
            "tool_calls": [{"tool": "get_org_chart", "args": {"department": "Engineering"}}],
            "tool_results": [{"department": "Engineering", "head": "Sofia Chen", "teams": ["Platform", "Backend", "Frontend", "QA"], "total_headcount": 48}],
            "final_response": "The Engineering department is led by Sofia Chen with 48 team members across four teams: Platform (12), Backend (15), Frontend (14), and QA (7). Platform and Backend report directly to Engineering Leads, while Frontend and QA have their own team leads."
        },
        {
            "user": "When is the next company holiday?",
            "assistant": "Checking the team calendar for upcoming holidays and company-wide events.",
            "tool_calls": [{"tool": "tool_get_team_calendar", "args": {"scope": "company_wide", "days_ahead": 30}}],
            "tool_results": [{"next_holiday": {"name": "San Juan", "date": "2026-06-24", "type": "regional"}, "upcoming": [{"name": "Summer Party", "date": "2026-07-04"}]}],
            "final_response": "The next company holiday is San Juan on June 24, 2026, which is a regional holiday (Catalonia). The Summer Party is also scheduled for July 4."
        },
        {
            "user": "List recent hires in the Marketing team",
            "assistant": "Let me pull up the most recent hires for Marketing.",
            "tool_calls": [{"tool": "tool_get_recent_hires", "args": {"department": "Marketing", "days": 90}}],
            "tool_results": [{"recent_hires": [{"name": "Lucia Vega", "role": "Content Strategist", "start_date": "2026-04-01"}, {"name": "Omar Nasir", "role": "Growth Marketer", "start_date": "2026-05-15"}]}],
            "final_response": "Two recent hires joined Marketing in the last 90 days: Lucia Vega started as Content Strategist on April 1, and Omar Nasir joined as Growth Marketer on May 15."
        }
    ],

    # ── Payroll Specialist (5 examples) ────────────────────────────────────
    "payroll_specialist": [
        {
            "user": "Process March payroll",
            "assistant": "I'll initiate the March payroll cycle. Before processing, I need to confirm — shall I proceed with all 87 employees on the standard cycle?",
            "tool_calls": [{"tool": "tool_create_payroll_cycle", "args": {"period": "March 2026", "pay_date": "2026-03-31"}}],
            "tool_results": [{"cycle_id": "paycycle-mar-2026", "employees": 87, "total_gross": 426500.00, "status": "draft"}],
            "final_response": "The March 2026 payroll cycle has been created in draft status. It covers 87 employees with a total gross of €426,500.00. To proceed, I need your explicit confirmation before processing. Would you like me to process this cycle?"
        },
        {
            "user": "Calculate tax for 45000 EUR salary in Spain",
            "assistant": "Let me look up the current Spanish tax rules and calculate the deductions for a €45,000 gross annual salary.",
            "tool_calls": [{"tool": "tool_get_tax_rules", "args": {"country": "ES", "year": 2026}}],
            "tool_results": [{"irpf_brackets": [{"to": 12450, "rate": 0.19}, {"to": 20200, "rate": 0.24}, {"to": 35200, "rate": 0.30}, {"to": 60000, "rate": 0.37}], "seguridad_social_employee": 0.0635}],
            "final_response": "For a €45,000 gross salary in Spain: IRPF withholding = €10,639.50 (effective ~23.64%), Seguridad Social = €2,857.50 (6.35%), net monthly salary = approximately €2,625.25 (12 payments). The effective IRPF rate is 23.64%."
        },
        {
            "user": "Generate March payslip for Elena Martinez",
            "assistant": "I'll retrieve Elena Martinez's payslip for March 2026.",
            "tool_calls": [{"tool": "tool_get_payslip", "args": {"employee_id": "emp-elena-m", "period": "2026-03"}}],
            "tool_results": [{"employee": "Elena Martinez", "gross": 3800.00, "irpf": 798.00, "ss_employee": 241.30, "net": 2760.70, "deductions_detail": {"irpf_rate": 0.21, "complemento_transporte": 80.00}}],
            "final_response": "Elena Martinez's March 2026 payslip: Gross €3,800.00 | IRPF (21%) -€798.00 | SS Employee -€241.30 | Transport Allowance +€80.00 | Net €2,760.70."
        },
        {
            "user": "Apply a 5% raise to all Backend engineers",
            "assistant": "Before applying a bulk salary increase, let me verify the Backend team composition and the total cost impact.",
            "tool_calls": [{"tool": "search_employees", "args": {"department": "Engineering", "team": "Backend"}}],
            "tool_results": [{"team": "Backend", "members": 15, "current_total_salary": 72000.00, "avg_salary": 4800}],
            "final_response": "The Backend team has 15 members with a current total monthly salary of €72,000. A 5% raise would increase monthly costs by €3,600 (€43,200 annually). I need your confirmation to proceed. This requires manager and finance approval before execution."
        },
        {
            "user": "Create a bonus of 2000 EUR for Carlos for Q1 performance",
            "assistant": "I'll create a bonus payment for Carlos linked to Q1 performance.",
            "tool_calls": [{"tool": "tool_create_bonus", "args": {"employee_id": "emp-carlos-r", "amount": 2000.00, "reason": "Q1 performance bonus", "period": "2026-Q1"}}],
            "tool_results": [{"bonus_id": "bon-q1-carlos", "status": "pending_approval", "tax_impact": "Bonus taxed at applicable IRPF rate"}],
            "final_response": "A €2,000 bonus for Carlos Ruiz has been created as pending approval (bon-q1-carlos). This will be included in the next payroll cycle upon approval. The bonus is subject to IRPF withholding per standard rules."
        }
    ],

    # ── IT Helpdesk (5 examples) ───────────────────────────────────────────
    "it_helpdesk": [
        {
            "user": "Create a ticket for John's laptop issue",
            "assistant": "I'll create an IT ticket for John's laptop problem. What specific issue are you seeing?",
            "tool_calls": [{"tool": "create_it_ticket", "args": {"employee_id": "emp-john-d", "category": "Hardware", "summary": "Laptop not charging", "priority": "medium"}}],
            "tool_results": [{"ticket_id": "IT-2026-0452", "status": "open", "assigned_to": "Helpdesk L1"}],
            "final_response": "Ticket IT-2026-0452 has been created for John's laptop charging issue, categorized as Hardware (medium priority). It's been assigned to L1 helpdesk. Average resolution time for hardware issues is 4 hours."
        },
        {
            "user": "Search KB for VPN setup",
            "assistant": "Let me search the knowledge base for VPN setup articles.",
            "tool_calls": [{"tool": "search_it_knowledge_base", "args": {"query": "VPN setup configuration", "limit": 5}}],
            "tool_results": [{"articles": [{"id": "KB-1042", "title": "VPN Setup Guide — Windows", "relevance": 0.95}, {"id": "KB-1043", "title": "VPN Setup Guide — macOS", "relevance": 0.93}, {"id": "KB-1180", "title": "Troubleshooting VPN Connection Issues", "relevance": 0.87}]}],
            "final_response": "I found 3 relevant KB articles: 1) VPN Setup Guide — Windows (KB-1042), 2) VPN Setup Guide — macOS (KB-1043), 3) Troubleshooting VPN Connection Issues (KB-1180). Which operating system are you using?"
        },
        {
            "user": "What assets does Maria in Design have?",
            "assistant": "Let me look up the IT assets assigned to Maria.",
            "tool_calls": [{"tool": "get_it_assets", "args": {"employee_id": "emp-maria-l"}}],
            "tool_results": [{"assigned_assets": [{"type": "laptop", "model": "MacBook Pro 16\" M3", "assigned": "2025-09-01"}, {"type": "monitor", "model": "Dell U2723QE 27\"", "assigned": "2025-09-01"}, {"type": "software", "name": "Adobe Creative Suite", "license": "CC-ENT-2025"}]}],
            "final_response": "Maria has three IT assets assigned: a MacBook Pro 16\" M3 (since Sep 2025), a Dell U2723QE 27\" monitor, and an Adobe Creative Suite enterprise license. All hardware is under warranty until September 2026."
        },
        {
            "user": "Show me ticket statistics for this month",
            "assistant": "Retrieving IT ticket statistics for the current month.",
            "tool_calls": [{"tool": "tool_get_ticket_stats", "args": {"period": "2026-06"}}],
            "tool_results": [{"period": "June 2026", "open": 12, "in_progress": 8, "resolved": 34, "avg_resolution_hours": 6.2, "sla_breach_pct": 4.0}],
            "final_response": "June 2026 IT ticket stats: 12 open, 8 in progress, 34 resolved. Average resolution time is 6.2 hours with a 4% SLA breach rate. Top categories: Software (38%), Hardware (27%), Access (22%)."
        },
        {
            "user": "Suggest a solution for recurring Wi-Fi drops on the 4th floor",
            "assistant": "Let me search for similar resolved tickets and suggest a solution.",
            "tool_calls": [{"tool": "suggest_it_solution", "args": {"issue": "recurring Wi-Fi drops 4th floor", "category": "Network"}}],
            "tool_results": [{"similar_tickets": 3, "suggested_solution": "Check access point AP-4F-02 for channel interference. Previous resolution: reconfigured to 5GHz channel 36, replaced faulty PoE injector.", "confidence": 0.85}],
            "final_response": "Based on 3 similar resolved tickets, the likely cause is channel interference on access point AP-4F-02. The previous fix was reconfiguring to 5GHz channel 36 and replacing a faulty PoE injector (85% confidence). I recommend dispatching a technician to inspect AP-4F-02."
        }
    ],

    # ── Recruiter Pro (5 examples) ─────────────────────────────────────────
    "recruiter_pro": [
        {
            "user": "Create a job posting for Senior Frontend Developer",
            "assistant": "I'll create a job posting for a Senior Frontend Developer. What are the key requirements?",
            "tool_calls": [{"tool": "tool_create_job_posting", "args": {"title": "Senior Frontend Developer", "department": "Engineering", "location": "Barcelona", "type": "full-time", "requirements": ["React 5+ years", "TypeScript", "CSS-in-JS", "CI/CD"]}}],
            "tool_results": [{"job_id": "job-2026-0034", "status": "published", "applications_count": 0}],
            "final_response": "The Senior Frontend Developer posting (job-2026-0034) has been published in Barcelona, full-time. Required skills: 5+ years React, TypeScript, CSS-in-JS, CI/CD experience. I can also add a salary range and benefits section — would you like me to add those?"
        },
        {
            "user": "Show top 5 candidates for the UX Designer role",
            "assistant": "Ranking candidates for the UX Designer position by fit score.",
            "tool_calls": [{"tool": "rank_candidates", "args": {"job_id": "job-2026-0018", "top_n": 5}}],
            "tool_results": [{"rankings": [{"name": "Anna Bergstrom", "score": 92, "stage": "interview"}, {"name": "Pablo Mendez", "score": 88, "stage": "interview"}, {"name": "Clara Weiss", "score": 85, "stage": "screening"}, {"name": "Javier Ortega", "score": 79, "stage": "screening"}, {"name": "Nina Johansson", "score": 76, "stage": "applied"}]}],
            "final_response": "Top 5 candidates for UX Designer: 1) Anna Bergstrom — 92% (interview stage), 2) Pablo Mendez — 88% (interview), 3) Clara Weiss — 85% (screening), 4) Javier Ortega — 79% (screening), 5) Nina Johansson — 76% (applied). Anna and Pablo are already in interview rounds."
        },
        {
            "user": "Move candidate Clara Weiss to interview stage",
            "assistant": "I'll advance Clara Weiss from screening to the interview stage for the UX Designer role.",
            "tool_calls": [{"tool": "tool_move_candidate_stage", "args": {"candidate_id": "cand-clara-w", "job_id": "job-2026-0018", "new_stage": "interview"}}],
            "tool_results": [{"candidate": "Clara Weiss", "previous_stage": "screening", "new_stage": "interview", "days_in_screening": 4}],
            "final_response": "Clara Weiss has been moved from screening to interview stage for the UX Designer role. She spent 4 days in screening. I can now schedule her interview — would you like me to find available slots with the hiring manager?"
        },
        {
            "user": "Schedule an interview with Pablo Mendez for Friday",
            "assistant": "Let me schedule the interview for Pablo Mendez on Friday. What time works best?",
            "tool_calls": [{"tool": "tool_schedule_interview", "args": {"candidate_id": "cand-pablo-m", "job_id": "job-2026-0018", "date": "2026-06-12", "interviewers": ["emp-sofia-c"]}}],
            "tool_results": [{"interview_id": "int-2026-0182", "status": "scheduled", "date": "2026-06-12T10:00:00", "duration_minutes": 60, "location": "Google Meet"}],
            "final_response": "Interview with Pablo Mendez has been scheduled for Friday, June 12 at 10:00 AM (60 minutes, Google Meet). The hiring manager Sofia Chen will conduct the interview. I'll send calendar invites to both parties."
        },
        {
            "user": "Generate interview questions for the DevOps Engineer role",
            "assistant": "I'll generate role-specific interview questions based on the DevOps Engineer job requirements.",
            "tool_calls": [{"tool": "generate_interview_questions", "args": {"job_id": "job-2026-0029", "categories": ["technical", "behavioral", "scenario"]}}],
            "tool_results": [{"questions": [{"type": "technical", "q": "Explain how you would set up a CI/CD pipeline for a microservices architecture using Kubernetes and Helm."}, {"type": "behavioral", "q": "Describe a time you resolved a production incident under pressure. What steps did you take?"}, {"type": "scenario", "q": "You discover a critical security vulnerability in the deployment pipeline one hour before a scheduled release. What do you do?"}]}],
            "final_response": "Here are 3 interview questions for the DevOps Engineer role: [Technical] 'Explain how you would set up a CI/CD pipeline for a microservices architecture using Kubernetes and Helm.' [Behavioral] 'Describe a time you resolved a production incident under pressure.' [Scenario] 'You discover a critical security vulnerability in the pipeline one hour before release. What do you do?'"
        }
    ],

    # ── Sales Coach (5 examples) ───────────────────────────────────────────
    "sales_coach": [
        {
            "user": "Score the new lead from Acme Corp",
            "assistant": "I'll evaluate Acme Corp as a lead using our scoring model.",
            "tool_calls": [{"tool": "score_lead", "args": {"company": "Acme Corp", "industry": "Manufacturing", "employees": 450, "annual_revenue": "80M", "source": "inbound"}}],
            "tool_results": [{"lead_score": 78, "tier": "qualified", "factors": {"company_size": 0.8, "industry_match": 0.7, "budget_indicator": 0.85, "timeline": 0.75}}],
            "final_response": "Acme Corp scores 78/100 — qualified tier. Key factors: strong budget indicator (0.85), good company fit (0.80), industry match (0.70), and reasonable timeline (0.75). I recommend creating this lead and assigning it to an enterprise AE."
        },
        {
            "user": "Show me the current pipeline overview",
            "assistant": "Retrieving the full sales pipeline overview.",
            "tool_calls": [{"tool": "get_pipeline_overview", "args": {}}],
            "tool_results": [{"pipeline_stages": {"prospecting": 24, "qualification": 18, "proposal": 12, "negotiation": 7, "closed_won": 0}, "total_value": 2450000, "weighted_value": 820000, "avg_deal_size": 51000}],
            "final_response": "Current pipeline: 24 leads prospecting, 18 in qualification, 12 in proposal, 7 in negotiation. Total pipeline value is €2.45M with a weighted value of €820K. Average deal size: €51K. The strongest stage is negotiation with 7 deals at a combined €640K."
        },
        {
            "user": "Generate a follow-up email for the Enterprise pipeline",
            "assistant": "I'll generate a follow-up email template for enterprise leads that have gone silent.",
            "tool_calls": [{"tool": "generate_email_template", "args": {"stage": "proposal", "audience": "enterprise", "tone": "professional", "goal": "re_engagement"}}],
            "tool_results": [{"subject": "Checking in — your {solution} proposal", "body": "Hi {first_name}, I wanted to follow up on the proposal we shared on {date}. Our team is excited about the opportunity to support {company} with {key_value_prop}. Do you have 15 minutes this week to discuss any questions or next steps? Best regards, {sender_name}"}],
            "final_response": "Here's your email template — Subject: 'Checking in — your {solution} proposal'. Body opens with a personal check-in, references the key value proposition, and offers a 15-minute call. Use the merge fields {first_name}, {company}, {solution}, {date}, and {key_value_prop} when sending."
        },
        {
            "user": "What actions should I take on the stalled TechVentures deal?",
            "assistant": "Analyzing the stalled TechVentures deal and suggesting next-best-actions.",
            "tool_calls": [{"tool": "suggest_sales_action", "args": {"deal_id": "deal-techventures-01", "stalled_days": 32}}],
            "tool_results": [{"suggested_actions": [{"action": "Send case study from similar manufacturing client", "impact": "high", "effort": "low"}, {"action": "Schedule a demo with their technical team", "impact": "high", "effort": "medium"}, {"action": "Offer a 2-week pilot", "impact": "medium", "effort": "high"}]}],
            "final_response": "TechVentures deal has been stalled for 32 days. Top recommendations: 1) [HIGH impact, LOW effort] Send the manufacturing case study — similar clients saw 30% faster onboarding, 2) [HIGH, MEDIUM] Schedule a technical demo for their engineering team, 3) [MEDIUM, HIGH] Offer a 2-week pilot."
        },
        {
            "user": "Create a lead for GlobalTech Solutions from the conference",
            "assistant": "I'll create a lead for GlobalTech Solutions with conference as the source.",
            "tool_calls": [{"tool": "create_lead", "args": {"company": "GlobalTech Solutions", "contact": "James Whitfield", "title": "VP Engineering", "source": "conference", "event": "SaaS Summit Barcelona 2026"}}],
            "tool_results": [{"lead_id": "lead-2026-0157", "status": "new", "assigned_to": "emp-david-p"}],
            "final_response": "Lead created — GlobalTech Solutions (lead-2026-0157), contact James Whitfield, VP Engineering, sourced from SaaS Summit Barcelona 2026. Assigned to David Park. I suggest following up within 24 hours while the conference is still fresh."
        }
    ],

    # ── Performance Coach (5 examples) ─────────────────────────────────────
    "performance_coach": [
        {
            "user": "Create Q2 OKRs for the Marketing team",
            "assistant": "I'll create Q2 Objectives and Key Results for the Marketing team. Let me first check existing Q1 results for context.",
            "tool_calls": [{"tool": "tool_get_team_okrs", "args": {"department": "Marketing", "period": "2026-Q1"}}],
            "tool_results": [{"team_okrs": {"objective": "Increase brand awareness in DACH region", "key_results": [{"kr": "Grow LinkedIn followers by 25%", "progress": 0.88}, {"kr": "Publish 12 thought leadership articles", "progress": 1.0}, {"kr": "Generate 200 MQLs from DACH", "progress": 0.72}]}}],
            "final_response": "Based on Q1 Marketing OKRs (88% LinkedIn growth, 100% articles published, 72% MQL target), I recommend Q2 OKRs: [Objective 1] 'Accelerate pipeline from DACH region' — KR1: Convert 150 MQLs to SQLs, KR2: Run 3 DACH-targeted webinars, KR3: Achieve 15% conversion rate. [Objective 2] 'Strengthen content engine' — KR1: Launch weekly newsletter, KR2: Produce 10 customer case studies, KR3: Increase organic traffic 30%."
        },
        {
            "user": "Generate a development plan for Maria",
            "assistant": "I'll create a personalized development plan for Maria based on her role and career goals.",
            "tool_calls": [{"tool": "get_employee_profile", "args": {"employee_id": "emp-maria-l"}}],
            "tool_results": [{"employee": "Maria Lopez", "role": "UI Designer", "tenure": "2 years", "skills": ["Figma", "Design Systems", "User Research"], "goal": "Lead Designer in 18 months"}],
            "final_response": "Development plan for Maria Lopez (UI Designer → Lead Designer in 18 months): [Month 1-3] Complete 'Design Leadership' course, shadow 2 design reviews. [Month 3-6] Lead a small design initiative with 1 junior, take 'Data-Driven Design' certification. [Month 6-12] Mentor a junior designer, present design strategy to stakeholders, attend 1 design conference. [Month 12-18] Own a full product redesign end-to-end, build and present a design vision document."
        },
        {
            "user": "Suggest goal adjustments for the Platform team",
            "assistant": "Reviewing Platform team OKR progress and suggesting adjustments.",
            "tool_calls": [{"tool": "suggest_goal_adjustments", "args": {"team": "Platform", "period": "2026-Q2"}}],
            "tool_results": [{"current_okrs": [{"kr": "Reduce API latency to <50ms p95", "progress": 0.4, "suggested_adjustment": "Extend timeline to end of Q3 due to dependency on database migration"}, {"kr": "Deploy 3 new microservices", "progress": 0.85, "suggested_adjustment": "On track, consider stretch goal of 4"}]}],
            "final_response": "Two adjustments recommended: 1) API latency KR at 40% progress — extend to Q3 due to the database migration dependency (this is a valid blocker). 2) Microservices KR at 85% — on track, suggest a stretch goal of 4 services instead of 3. Would you like me to update these in the system?"
        },
        {
            "user": "Create a performance review for Carlos Ruiz",
            "assistant": "I'll set up a performance review for Carlos Ruiz. Let me gather his recent achievements and kudos first.",
            "tool_calls": [{"tool": "tool_get_kudos_received", "args": {"employee_id": "emp-carlos-r", "months": 6}}],
            "tool_results": [{"kudos_count": 8, "themes": ["Team collaboration", "Mentoring juniors", "Production incident response"], "avg_rating": 4.7}],
            "final_response": "Carlos has received 8 kudos in 6 months with a 4.7 average rating. Key themes: team collaboration, mentoring juniors, and production incident handling. I can now create the review — I'll structure it with sections for: Technical Excellence, Collaboration, Mentorship Impact, and Goals for Next Period. Would you like to add any specific discussion points?"
        },
        {
            "user": "What SMART goals should the QA team set for Q3?",
            "assistant": "Let me generate SMART goals for the QA team considering their current metrics and team composition.",
            "tool_calls": [{"tool": "generate_smart_goals", "args": {"team": "QA", "period": "2026-Q3", "context": "improve test coverage and reduce bug escape rate"}}],
            "tool_results": [{"smart_goals": [{"goal": "Increase automated test coverage from 68% to 80% by end of Q3", "specific": "Automated test coverage for core user flows", "measurable": "Coverage percentage via SonarQube", "time_bound": "September 30, 2026"}, {"goal": "Reduce production bug escape rate from 4.2 to under 2.0 per sprint", "specific": "Bugs reported in production within 2 weeks of release", "measurable": "Bug count per sprint from Jira", "time_bound": "By end of Q3"}]}],
            "final_response": "Two SMART goals for QA Q3: [Goal 1] Increase automated test coverage from 68% to 80% by September 30, measured via SonarQube — requires adding ~30 new E2E tests for core flows. [Goal 2] Reduce production bug escape rate from 4.2 to under 2.0 per sprint by end of Q3, measured via Jira bug reports. Both are Specific, Measurable, Achievable, Relevant, and Time-bound."
        }
    ],

    # ── Onboarding Buddy (5 examples) ──────────────────────────────────────
    "onboarding_buddy": [
        {
            "user": "Generate an onboarding plan for the new backend engineer",
            "assistant": "I'll create a personalized onboarding plan for the new Backend Engineer.",
            "tool_calls": [{"tool": "generate_onboarding_plan", "args": {"role": "Backend Engineer", "department": "Engineering", "start_date": "2026-06-15"}}],
            "tool_results": [{"week_1": ["Day 1: Welcome meeting, desk setup, HR orientation", "Day 2: Tech stack overview, repo access, local setup", "Day 3-5: Shadow senior engineer, first small PR"]}, {"week_2": ["Pair programming sessions", "Architecture deep-dive", "First story assigned"]}],
            "final_response": "Onboarding plan for Backend Engineer starting June 15: **Week 1** — Day 1: Welcome meeting with manager, desk/equipment setup, HR orientation. Day 2: Tech stack walkthrough, GitHub access, environment setup. Days 3-5: Shadow senior engineer on active sprint, submit first small PR. **Week 2** — Pair programming with 2 team members, architecture deep-dive session, first user story assigned. I've also created IT tickets for laptop and access provisioning."
        },
        {
            "user": "Assign a buddy for Carlos starting next Monday",
            "assistant": "Let me find an appropriate onboarding buddy for Carlos from his new team.",
            "tool_calls": [{"tool": "assign_onboarding_buddy", "args": {"new_hire_id": "emp-carlos-r", "department": "Backend", "criteria": ["tenure_12m_plus", "same_team", "positive_kudos"]}}],
            "tool_results": [{"buddy": {"name": "Rosa Jimenez", "role": "Senior Backend Engineer", "tenure": "4 years", "kudos_received": 15, "previous_buddies": 3}}],
            "final_response": "Rosa Jimenez has been assigned as Carlos's onboarding buddy. She's a Senior Backend Engineer with 4 years tenure, 15 kudos received, and has successfully mentored 3 previous new hires. I'll send both of them an introduction and a first-week buddy checklist."
        },
        {
            "user": "Enroll the new Data Analyst in mandatory training",
            "assistant": "I'll enroll the new Data Analyst in all mandatory courses and role-relevant training.",
            "tool_calls": [{"tool": "tool_enroll_in_course", "args": {"employee_id": "emp-nina-j", "courses": ["GDPR Basics", "Data Security Level 1", "SQL Advanced", "Tableau Fundamentals"]}}],
            "tool_results": [{"enrolled": 4, "courses": [{"name": "GDPR Basics", "deadline": "2026-07-01"}, {"name": "Data Security Level 1", "deadline": "2026-07-01"}, {"name": "SQL Advanced", "deadline": "2026-07-15"}, {"name": "Tableau Fundamentals", "deadline": "2026-07-15"}]}],
            "final_response": "Nina has been enrolled in 4 courses: GDPR Basics and Data Security Level 1 (compliance deadline July 1, 2026), SQL Advanced and Tableau Fundamentals (role-specific, deadline July 15, 2026). I've added these to her onboarding task tracker."
        },
        {
            "user": "Set up IT access for the new hire Sofia starting tomorrow",
            "assistant": "Creating IT setup tickets for Sofia's first-day needs.",
            "tool_calls": [{"tool": "create_it_ticket", "args": {"employee_id": "emp-sofia-n", "category": "Access", "summary": "New hire setup: email, VPN, GitHub, Slack, Jira", "priority": "high"}}],
            "tool_results": [{"ticket_id": "IT-2026-0453", "status": "open", "estimated_completion": "2026-06-09T09:00:00"}],
            "final_response": "IT setup ticket IT-2026-0453 created for Sofia: email account, VPN access, GitHub org invite, Slack workspace, Jira access. Estimated completion by tomorrow 9:00 AM. I've also added the standard software stack: VS Code, Docker, Postman."
        },
        {
            "user": "Create onboarding tasks for the Frontend team lead",
            "assistant": "I'll create the manager's onboarding task list to ensure nothing falls through the cracks.",
            "tool_calls": [{"tool": "tool_create_project_task", "args": {"project": "Onboarding", "tasks": ["Prep desk and equipment by day -1", "Send welcome email with first-day details", "Schedule 1:1 at end of week 1", "Schedule 30-day check-in", "Assign first project by end of week 2"]}}],
            "tool_results": [{"project": "Onboarding — Frontend Team Lead", "tasks_created": 5, "due_dates": {"Prep desk": "2026-06-14", "Welcome email": "2026-06-14", "Week 1 1:1": "2026-06-19", "30-day check-in": "2026-07-15", "First project": "2026-06-26"}}],
            "final_response": "5 onboarding tasks created for the Frontend Team Lead's manager: 1) Prep desk/equipment by June 14, 2) Send welcome email by June 14, 3) Schedule week 1 1:1 by June 19, 4) Schedule 30-day check-in by July 15, 5) Assign first project by June 26. All tasks are tracked in the 'Onboarding' project board."
        }
    ],

    # ── Compliance Officer (5 examples) ────────────────────────────────────
    "compliance_officer": [
        {
            "user": "Validate FUNDAE submission for the Q1 training batch",
            "assistant": "I'll validate the Q1 training submissions against FUNDAE requirements.",
            "tool_calls": [{"tool": "tool_validate_fundae", "args": {"period": "2026-Q1"}}],
            "tool_results": [{"status": "review_required", "issues": [{"course": "Leadership 101", "issue": "Missing attendance record for 2 sessions", "employees_affected": 3}, {"course": "Python Advanced", "issue": "Course duration exceeds FUNDAE max hours by 5", "employees_affected": 8}]}],
            "final_response": "Q1 FUNDAE validation found 2 issues: 1) Leadership 101 — missing attendance records for 2 sessions (3 employees affected). 2) Python Advanced — course duration exceeds FUNDAE maximum hours by 5 (8 employees affected). Both need correction before submission. Would you like me to flag these for the training coordinator?"
        },
        {
            "user": "Check GDPR compliance for candidate data retention",
            "assistant": "I'll audit candidate data retention against GDPR requirements.",
            "tool_calls": [{"tool": "tool_get_compliance_status", "args": {"domain": "gdpr", "scope": "candidate_data_retention"}}],
            "tool_results": [{"status": "partial_compliance", "findings": [{"rule": "Article 5(1)(e)", "issue": "127 candidate records older than 12 months without documented retention justification"}, {"rule": "Article 17", "issue": "No automated deletion process for expired consent"}]}],
            "final_response": "GDPR compliance check found 2 issues: 1) Article 5(1)(e) — 127 candidate records exceed the 12-month retention period without documented justification. 2) Article 17 — no automated deletion process exists for candidates whose consent has expired. I recommend: (a) bulk anonymize or delete records older than 12 months, (b) implement automated consent expiry and deletion workflows."
        },
        {
            "user": "Show all contracts expiring in the next 30 days",
            "assistant": "Retrieving all contracts with expiration dates within the next 30 days.",
            "tool_calls": [{"tool": "tool_get_contracts", "args": {"status": "active", "expiring_within_days": 30}}],
            "tool_results": [{"expiring_contracts": [{"employee": "Elena Martinez", "type": "indefinido", "end_date": "2026-06-30", "notice_required": "15 days"}, {"employee": "contractor-vendor", "type": "mercantil", "end_date": "2026-07-05", "notice_required": "30 days"}]}],
            "final_response": "2 contracts expiring in the next 30 days: 1) Elena Martinez — indefinite contract, probation ends June 30 (15-day notice required). 2) Vendor/contractor agreement — expires July 5 (30-day notice required, already past deadline if not yet notified). Recommendation: immediate action on the vendor contract."
        },
        {
            "user": "Review expense report for policy compliance",
            "assistant": "I'll check the submitted expense report against the company expense policy.",
            "tool_calls": [{"tool": "tool_get_expense_summary", "args": {"report_id": "exp-2026-0142"}}],
            "tool_results": [{"report_id": "exp-2026-0142", "employee": "David Park", "total": 2450.00, "items": [{"category": "Travel", "amount": 850.00, "policy_limit": 800.00, "over_by": 50.00}, {"category": "Client dinner", "amount": 320.00, "policy_limit": 300.00, "over_by": 20.00}]}],
            "final_response": "Expense report exp-2026-0142 (David Park) has 2 policy violations: 1) Travel expense of €850 exceeds the €800 per-trip limit by €50 — requires manager justification. 2) Client dinner of €320 exceeds the €300 limit by €20 — requires receipt and attendee list. The remaining €1,280 in expenses are compliant."
        },
        {
            "user": "Are we compliant with Spanish labor law for overtime tracking?",
            "assistant": "Checking overtime tracking compliance against Estatuto de los Trabajadores requirements.",
            "tool_calls": [{"tool": "tool_get_compliance_status", "args": {"domain": "labor_law", "scope": "overtime_tracking"}}],
            "tool_results": [{"status": "compliant", "details": {"daily_records_required": True, "currently_tracked": True, "anomaly_flag": "3 employees exceeded 80h annual overtime limit (Art. 35.2 ET)", "employees_affected": ["emp-id-001", "emp-id-002", "emp-id-003"]}}],
            "final_response": "Overtime tracking is generally compliant with Spanish labor law — daily records are maintained as required. However, there is one anomaly: 3 employees have exceeded the 80-hour annual overtime limit under Article 35.2 of the Estatuto de los Trabajadores. This must be addressed: the employer must either compensate with rest time within 4 months or review workload allocation."
        }
    ],

    # ── Data Analyst (5 examples) ──────────────────────────────────────────
    "data_analyst": [
        {
            "user": "Show headcount trend for Engineering over the last 12 months",
            "assistant": "Retrieving monthly headcount data for the Engineering department.",
            "tool_calls": [{"tool": "get_headcount_trend", "args": {"department": "Engineering", "months": 12}}],
            "tool_results": [{"trend": [{"month": "2025-07", "headcount": 38}, {"month": "2025-10", "headcount": 41}, {"month": "2026-01", "headcount": 44}, {"month": "2026-04", "headcount": 47}, {"month": "2026-06", "headcount": 48}], "net_change": 10, "growth_pct": 26.3}],
            "final_response": "Engineering headcount grew from 38 to 48 over the last 12 months — a 26.3% increase (+10 people). Growth was steady at ~1 hire per month with a spike in Q1 2026 (+3). The current team breaks down as: Platform (12), Backend (15), Frontend (14), QA (7)."
        },
        {
            "user": "Analyze turnover rate by department for Q1",
            "assistant": "I'll analyze voluntary and involuntary turnover across departments for Q1.",
            "tool_calls": [{"tool": "get_turnover_analysis", "args": {"period": "2026-Q1", "group_by": "department"}}],
            "tool_results": [{"departments": [{"name": "Engineering", "headcount_start": 45, "departures": 2, "rate": 4.4}, {"name": "Marketing", "headcount_start": 18, "departures": 3, "rate": 16.7}, {"name": "Sales", "headcount_start": 22, "departures": 1, "rate": 4.5}, {"name": "HR", "headcount_start": 8, "departures": 0, "rate": 0.0}]}],
            "final_response": "Q1 2026 turnover rates: Marketing — 16.7% (3 departures from 18, above the 10% benchmark), Sales — 4.5%, Engineering — 4.4%, HR — 0%. Marketing's elevated rate warrants attention: 2 of the 3 departures cited 'career growth' and 1 was for 'compensation'. Recommend exit interview deep-dive for Marketing."
        },
        {
            "user": "Show diversity metrics across the company",
            "assistant": "Retrieving diversity and inclusion metrics from the HR system.",
            "tool_calls": [{"tool": "get_diversity_metrics", "args": {"scope": "company_wide", "year": 2026}}],
            "tool_results": [{"gender_ratio": {"female": 0.38, "male": 0.60, "non_binary": 0.02}, "leadership_gender": {"female": 0.25, "male": 0.73, "non_binary": 0.02}, "nationalities": 14, "age_distribution": {"under_30": 0.22, "30_44": 0.51, "45_plus": 0.27}}],
            "final_response": "Company-wide diversity metrics: Gender ratio — 38% female, 60% male, 2% non-binary. Leadership roles show 25% female representation (gap of 13pp vs. overall). 14 nationalities represented. Age distribution: 22% under 30, 51% ages 30-44, 27% ages 45+. The leadership gender gap is the primary area for improvement."
        },
        {
            "user": "What's the time-to-hire across all open roles?",
            "assistant": "Calculating time-to-hire metrics for all active job requisitions.",
            "tool_calls": [{"tool": "get_time_to_hire", "args": {"period": "2026", "group_by": "department"}}],
            "tool_results": [{"avg_time_to_hire_days": 34, "by_department": {"Engineering": 28, "Marketing": 42, "Sales": 31, "Finance": 45}, "benchmark": 30, "above_benchmark": ["Marketing", "Finance"]}],
            "final_response": "Average time-to-hire is 34 days (benchmark: 30 days). Engineering is fastest at 28 days. Marketing (42 days) and Finance (45 days) exceed the benchmark. The primary bottleneck for Marketing is candidate volume to screen ratio (8:1 applications per hire vs. 5:1 in Engineering)."
        },
        {
            "user": "Compare deal win rates across sales reps for Q2",
            "assistant": "Analyzing Q2 deal statistics by sales representative.",
            "tool_calls": [{"tool": "tool_get_deal_stats", "args": {"period": "2026-Q2", "group_by": "rep"}}],
            "tool_results": [{"reps": [{"name": "Ana Torres", "deals_won": 7, "win_rate": 0.58, "total_value": 420000}, {"name": "Luis Mendez", "deals_won": 5, "win_rate": 0.42, "total_value": 280000}, {"name": "Sara Koh", "deals_won": 9, "win_rate": 0.64, "total_value": 510000}]}],
            "final_response": "Q2 win rates by rep: Sara Koh leads at 64% (9 deals, €510K), followed by Ana Torres at 58% (7 deals, €420K), and Luis Mendez at 42% (5 deals, €280K). Sara's pipeline velocity is also highest at 22 days average deal cycle vs. team average of 31 days."
        }
    ],

    # ── Finance Manager (5 examples) ───────────────────────────────────────
    "finance_manager": [
        {
            "user": "Approve expense reports for the Marketing team this month",
            "assistant": "Let me pull up all pending Marketing expense reports for June.",
            "tool_calls": [{"tool": "tool_get_expense_summary", "args": {"department": "Marketing", "period": "2026-06", "status": "pending_approval"}}],
            "tool_results": [{"pending_reports": [{"id": "exp-2026-0155", "employee": "Lucia Vega", "amount": 420.00, "items": 3}, {"id": "exp-2026-0158", "employee": "Omar Nasir", "amount": 680.00, "items": 5}]}],
            "final_response": "2 pending Marketing expense reports: Lucia Vega — €420 (3 items, conference travel) — within policy. Omar Nasir — €680 (5 items, client entertainment) — within policy with receipts attached. Both appear compliant. Would you like me to approve both?"
        },
        {
            "user": "Show this month's financial ledger entries",
            "assistant": "Retrieving financial ledger entries for June 2026.",
            "tool_calls": [{"tool": "tool_get_financial_ledger", "args": {"period": "2026-06"}}],
            "tool_results": [{"entries": [{"type": "credit", "amount": 125000.00, "description": "Client payment — TechVentures"}, {"type": "debit", "amount": 86500.00, "description": "Payroll — June cycle"}, {"type": "debit", "amount": 12400.00, "description": "Cloud infrastructure"}, {"type": "credit", "amount": 45000.00, "description": "Client payment — Acme Corp"}]}],
            "final_response": "June 2026 financial ledger: Revenue — €170,000 (€125K TechVentures, €45K Acme Corp). Expenses — €98,900 (€86.5K June payroll, €12.4K cloud infra). Net income for June so far: €71,100. The month is 30% complete with 42% of expected revenue already recognized."
        },
        {
            "user": "Track time for the Platform team this week",
            "assistant": "Retrieving time logs for the Platform team for the current week.",
            "tool_calls": [{"tool": "tool_get_time_logs", "args": {"department": "Platform", "period": "2026-W23"}}],
            "tool_results": [{"team": "Platform", "total_hours": 420, "avg_per_person": 35, "project_breakdown": {"Core Platform": 240, "API Gateway": 110, "Internal Tools": 70}}],
            "final_response": "Platform team week 23: 420 total hours logged (avg 35h per person, 12 members). Project breakdown: Core Platform 240h (57%), API Gateway 110h (26%), Internal Tools 70h (17%). Overtime flagged: 2 members at 42h and 44h."
        },
        {
            "user": "Create an expense report for my Barcelona conference trip",
            "assistant": "I'll create an expense report for your Barcelona conference trip.",
            "tool_calls": [{"tool": "create_expense", "args": {"category": "Travel", "items": ["Round-trip train Madrid-Barcelona: 180 EUR", "Hotel 2 nights: 320 EUR", "Conference registration: 450 EUR", "Meals: 120 EUR"]}}],
            "tool_results": [{"expense_id": "exp-2026-0162", "total": 1070.00, "status": "draft", "policy_check": "passed"}],
            "final_response": "Expense report exp-2026-0162 created — total €1,070.00 (train €180, hotel €320, conference €450, meals €120). All items passed policy checks. Report is in draft — submit when ready for approval."
        },
        {
            "user": "Approve the finance team's expense reports for this week",
            "assistant": "Let me check all pending expense reports from the Finance team.",
            "tool_calls": [{"tool": "approve_expense", "args": {"department": "Finance", "period": "2026-W23", "status": "pending_approval"}}],
            "tool_results": [{"approved": 2, "rejected": 0, "reports": [{"id": "exp-2026-0145", "amount": 210.00, "status": "approved"}, {"id": "exp-2026-0148", "amount": 145.00, "status": "approved"}], "total_approved": 355.00}],
            "final_response": "2 Finance team expense reports approved: exp-2026-0145 (€210, office supplies), exp-2026-0148 (€145, team lunch). Total approved: €355.00. Both were within policy limits with proper receipts attached."
        }
    ]
}


async def get_few_shot_examples(agent_type: str, max_examples: int = 3) -> List[Dict]:
    """Return the best few-shot examples for a given agent type.

    Returns the most recently added examples first (they appear last in the list).
    """
    examples = FEW_SHOT_EXAMPLES.get(agent_type, [])
    if not examples:
        logger.warning(f"No few-shot examples found for agent_type='{agent_type}'")
        return []

    # Return last N examples (most recently added) up to max_examples
    selected = examples[-max_examples:] if len(examples) > max_examples else list(examples)
    # Reverse so most recent (last in list) comes first
    selected.reverse()
    return selected


async def inject_few_shot_examples(
    system_prompt: str,
    agent_type: str,
    max_examples: int = 3,
) -> str:
    """Format few-shot examples and inject them into the system prompt.

    The examples are appended after a separator to the system prompt.
    """
    examples = await get_few_shot_examples(agent_type, max_examples)
    if not examples:
        return system_prompt

    formatted = []
    for i, ex in enumerate(examples, 1):
        block = []
        block.append(f"Example {i}:")
        block.append(f"User: {ex['user']}")
        block.append(f"Assistant: {ex['assistant']}")
        if ex.get("tool_calls"):
            tool_strs = []
            for tc in ex["tool_calls"]:
                tool_strs.append(f"  - {tc['tool']}({tc['args']})")
            block.append("Tool calls:\n" + "\n".join(tool_strs))
        if ex.get("tool_results"):
            block.append(f"Tool results: {ex['tool_results']}")
        block.append(f"Final response: {ex['final_response']}")
        formatted.append("\n".join(block))

    injection = (
        "\n\n--- FEW-SHOT EXAMPLES ---\n"
        "Below are examples of how you should respond to user queries. "
        "Follow this pattern: acknowledge the request, use the appropriate tool, "
        "interpret results, and provide a complete, helpful response.\n\n"
        + "\n\n".join(formatted)
        + "\n--- END EXAMPLES ---"
    )

    return system_prompt + injection
