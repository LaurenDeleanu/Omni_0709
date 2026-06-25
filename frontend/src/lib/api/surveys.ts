// src/lib/api/surveys.ts — Employee Surveys API
import { fetchClient } from './client';

export const SurveysAPI = {
  createSurvey: (data: any) => fetchClient("/surveys", { method: "POST", body: JSON.stringify(data) }),
  listSurveys: () => fetchClient("/surveys"),
  submitResponse: (surveyId: string, data: any) => fetchClient(`/surveys/${surveyId}/responses`, { method: "POST", body: JSON.stringify(data) }),
  getSentiment: (surveyId: string) => fetchClient(`/surveys/${surveyId}/sentiment`),
  getTrends: () => fetchClient("/surveys/trends"),
};
