export function slugify(value: string): string {
  return (
    value
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48) || "job"
  );
}

export function fnv1a(value: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function jobId(title: string, text: string, skills: string[]): string {
  const sorted = [...skills].map((s) => s.trim()).sort((a, b) => a.localeCompare(b));
  return `${slugify(title)}-${fnv1a(`${title.trim()}|${text.trim()}|${sorted.join(",")}`)}`;
}

export interface JobPreset {
  title: string;
  text: string;
  skills: string[];
}

export const JOB_PRESETS: JobPreset[] = [
  {
    title: "Backend Engineer",
    text: "Design, build and operate backend services and APIs. Own data models, performance and reliability in production.",
    skills: ["Python", "Go", "PostgreSQL", "Docker", "REST APIs"],
  },
  {
    title: "Frontend Engineer",
    text: "Build accessible, fast web interfaces. Work closely with design and backend teams on product features.",
    skills: ["TypeScript", "JavaScript", "React", "CSS", "HTML"],
  },
  {
    title: "ML Engineer",
    text: "Train, evaluate and ship machine learning models. Build data pipelines and model serving infrastructure.",
    skills: ["Python", "PyTorch", "Jupyter Notebook", "SQL", "Docker"],
  },
  {
    title: "Competitive Programmer",
    text: "Solve algorithmic problems under time constraints. Strong grasp of data structures and complexity analysis.",
    skills: ["C++", "Python", "Algorithms", "Data Structures"],
  },
];
