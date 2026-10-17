
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, rows, DEFAULT_PROJECT_ID } from "@/lib/api";

export interface Project {
  id: string;
  owner_id?: string;
  name: string;
  description?: string | null;
  created_at?: string;
  updated_at?: string;
}

interface ProjectContextValue {
  projects: Project[];
  selectedProjectId: string;
  selectedProject: Project | null;
  loading: boolean;
  creating: boolean;
  error: string;
  setSelectedProjectId: (id: string) => void;
  refreshProjects: () => Promise<void>;
  createProject: (name: string, description: string) => Promise<Project>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);
const STORAGE_KEY = "finthesara_selected_project_id";

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectIdState] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const setSelectedProjectId = useCallback((id: string) => {
    setSelectedProjectIdState(id);

    try {
      if (id) {
        window.localStorage.setItem(STORAGE_KEY, id);
      } else {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // The selection still works if browser storage is unavailable.
    }
  }, []);

  const refreshProjects = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await api<unknown>("/projects");
      const list = rows<Project>(response).filter(
        (project) => project && typeof project.id === "string",
      );

      setProjects(list);

      let savedId = "";
      try {
        savedId =
          window.localStorage.getItem(STORAGE_KEY) ||
          DEFAULT_PROJECT_ID;
      } catch {
        savedId = DEFAULT_PROJECT_ID;
      }

      const nextId = list.some((project) => project.id === savedId)
        ? savedId
        : list[0]?.id || "";

      setSelectedProjectId(nextId);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load projects.",
      );
    } finally {
      setLoading(false);
    }
  }, [setSelectedProjectId]);

  useEffect(() => {
    void refreshProjects();
  }, [refreshProjects]);

  const createProject = useCallback(
    async (name: string, description: string) => {
      const cleanName = name.trim();

      if (!cleanName) {
        throw new Error("Enter a project name.");
      }

      setCreating(true);
      setError("");

      try {
        const response = await api<unknown>("/projects", {
          method: "POST",
          body: JSON.stringify({
            name: cleanName,
            description: description.trim() || null,
          }),
        });

        const payload = response as {
          id?: string;
          project?: Project;
          data?: Project;
        };

        const created =
          payload?.project ||
          payload?.data ||
          (payload as Project);

        if (!created?.id) {
          await refreshProjects();
          throw new Error(
            "The API response did not contain the new project's ID.",
          );
        }

        setProjects((current) => [
          created,
          ...current.filter((item) => item.id !== created.id),
        ]);

        setSelectedProjectId(created.id);
        return created;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Could not create project.";
        setError(message);
        throw err;
      } finally {
        setCreating(false);
      }
    },
    [refreshProjects, setSelectedProjectId],
  );

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) || null,
    [projects, selectedProjectId],
  );

  const value = useMemo<ProjectContextValue>(
    () => ({
      projects,
      selectedProjectId,
      selectedProject,
      loading,
      creating,
      error,
      setSelectedProjectId,
      refreshProjects,
      createProject,
    }),
    [
      projects,
      selectedProjectId,
      selectedProject,
      loading,
      creating,
      error,
      setSelectedProjectId,
      refreshProjects,
      createProject,
    ],
  );

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjects() {
  const context = useContext(ProjectContext);

  if (!context) {
    throw new Error(
      "useProjects must be used inside ProjectProvider.",
    );
  }

  return context;
}
