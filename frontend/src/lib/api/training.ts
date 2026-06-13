// src/lib/api/training.ts — Training & LMS API
import { fetchClient } from './client';

export interface CourseCreate {
  title: string;
  description?: string;
  is_scorm?: boolean;
  scorm_version?: string;
  package_url?: string;
  min_duration_hours?: number;
  is_fundae_eligible?: boolean;
  category?: string;
}

export interface CourseUpdate {
  title?: string;
  description?: string;
  is_scorm?: boolean;
  scorm_version?: string;
  package_url?: string;
  min_duration_hours?: number;
  is_fundae_eligible?: boolean;
  category?: string;
}

export const TrainingAPI = {
  getCourses: (isFundaeEligible?: boolean) => {
    const query = isFundaeEligible !== undefined ? `?is_fundae_eligible=${isFundaeEligible}` : "";
    return fetchClient(`/training/courses${query}`);
  },
  getRecommendations: (userId: string) => fetchClient(`/training/recommendations/${userId}`),
  createCourse: (data: CourseCreate) => fetchClient("/training/courses", { method: "POST", body: JSON.stringify(data) }),
  updateCourse: (id: string, data: CourseUpdate) => fetchClient(`/training/courses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteCourse: (id: string) => fetchClient(`/training/courses/${id}`, { method: "DELETE" }),
  getEnrollments: (userId?: string) => {
    const query = userId ? `?user_id=${userId}` : "";
    return fetchClient(`/training/enrollments${query}`);
  },
  createEnrollment: (data: { user_id: string; course_id: string }) => fetchClient("/training/enrollments", { method: "POST", body: JSON.stringify(data) }),
  commitScormState: (enrollmentId: string, data: Record<string, unknown>) => fetchClient(`/training/enrollments/${enrollmentId}/scorm`, { method: "PATCH", body: JSON.stringify(data) }),
  validateFundae: (enrollmentId: string) => fetchClient(`/training/fundae/validate/${enrollmentId}`),
  exportFundaeXML: () => fetchClient("/training/fundae/export-xml")
};
