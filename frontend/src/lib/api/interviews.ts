// src/lib/api/interviews.ts — Recruitment Interviews & Scorecards API
import { fetchClient } from './client';

export interface Scorecard {
  id: string;
  candidate_id: string;
  interviewer_id: string;
  overall_recommendation: string;
  ratings?: any;
  feedback?: string;
  [key: string]: any;
}

export const InterviewsAPI = {
  getScorecards: () => fetchClient("/interviews/interview-scorecards"),
  createScorecard: (data: any) => fetchClient("/interviews/interview-scorecards", { method: "POST", body: JSON.stringify(data) }),
  getScorecard: (scorecardId: string) => fetchClient(`/interviews/interview-scorecards/${scorecardId}`),
  deleteScorecard: (scorecardId: string) => fetchClient(`/interviews/interview-scorecards/${scorecardId}`, { method: "DELETE" }),
  
  getKits: () => fetchClient("/interviews/interview-kits"),
  createKit: (data: any) => fetchClient("/interviews/interview-kits", { method: "POST", body: JSON.stringify(data) }),
  
  createEvaluation: (data: any) => fetchClient("/interviews/candidate-evaluations", { method: "POST", body: JSON.stringify(data) }),
  getCandidateEvaluations: (candidateId: string) => fetchClient(`/interviews/candidate-evaluations/${candidateId}`),
};
