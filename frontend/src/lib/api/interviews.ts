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
  getScorecards: () => fetchClient("/interview-scorecards"),
  createScorecard: (data: any) => fetchClient("/interview-scorecards", { method: "POST", body: JSON.stringify(data) }),
  getScorecard: (scorecardId: string) => fetchClient(`/interview-scorecards/${scorecardId}`),
  deleteScorecard: (scorecardId: string) => fetchClient(`/interview-scorecards/${scorecardId}`, { method: "DELETE" }),

  getKits: () => fetchClient("/interview-kits"),
  createKit: (data: any) => fetchClient("/interview-kits", { method: "POST", body: JSON.stringify(data) }),

  createEvaluation: (data: any) => fetchClient("/candidate-evaluations", { method: "POST", body: JSON.stringify(data) }),
  getCandidateEvaluations: (candidateId: string) => fetchClient(`/candidate-evaluations/${candidateId}`),
};
