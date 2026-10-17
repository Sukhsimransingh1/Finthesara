
"use client";

import { useState, type FormEvent } from "react";
import { FolderKanban, Plus, RefreshCw, X } from "lucide-react";
import { useProjects } from "./ProjectProvider";

export function ProjectSwitcher() {
  const {
    projects,
    selectedProjectId,
    setSelectedProjectId,
    loading,
    creating,
    error,
    refreshProjects,
    createProject,
  } = useProjects();

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");
    setSuccess("");

    try {
      const project = await createProject(name, description);
      setName("");
      setDescription("");
      setShowCreate(false);
      setSuccess(`Switched to ${project.name}.`);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Could not create project.",
      );
    }
  }

  return (
    <section className="project-switcher">
      <div className="project-switcher-heading">
        <span>
          <FolderKanban size={14} />
          ACTIVE PROJECT
        </span>
        <button
          type="button"
          className="project-icon-button"
          onClick={() => void refreshProjects()}
          disabled={loading}
          aria-label="Refresh projects"
          title="Refresh projects"
        >
          <RefreshCw size={13} className={loading ? "spin" : ""} />
        </button>
      </div>

      <select
        aria-label="Select active project"
        value={selectedProjectId}
        onChange={(event) => {
          setSelectedProjectId(event.target.value);
          setSuccess("");
        }}
        disabled={loading || projects.length === 0}
      >
        {loading && <option value="">Loading projects…</option>}
        {!loading && projects.length === 0 && (
          <option value="">No projects available</option>
        )}
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>

      {!showCreate ? (
        <button
          type="button"
          className="project-create-toggle"
          onClick={() => {
            setShowCreate(true);
            setFormError("");
            setSuccess("");
          }}
        >
          <Plus size={14} /> Create project
        </button>
      ) : (
        <form className="project-create-form" onSubmit={submit}>
          <div className="project-create-title">
            <b>New project</b>
            <button
              type="button"
              className="project-icon-button"
              onClick={() => setShowCreate(false)}
              aria-label="Cancel project creation"
            >
              <X size={14} />
            </button>
          </div>

          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Project name"
            aria-label="Project name"
            maxLength={120}
            required
            disabled={creating}
          />

          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Description (optional)"
            aria-label="Project description"
            rows={2}
            maxLength={2000}
            disabled={creating}
          />

          {formError && <p className="project-message error-text">{formError}</p>}

          <button
            className="btn primary project-submit"
            type="submit"
            disabled={creating || !name.trim()}
          >
            {creating ? "Creating…" : "Create and select"}
          </button>
        </form>
      )}

      {error && !showCreate && (
        <p className="project-message error-text">{error}</p>
      )}
      {success && <p className="project-message success-text">{success}</p>}
    </section>
  );
}
