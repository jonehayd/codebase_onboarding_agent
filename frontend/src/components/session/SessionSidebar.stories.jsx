import { fn } from "storybook/test";
import SessionSidebar from "./SessionSidebar";

const SESSIONS = [
  {
    id: 1,
    title: "Auth service review",
    repoName: "acme/auth-service",
    status: "completed",
    lastActive: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    isActive: true,
  },
  {
    id: 2,
    title: "Frontend onboarding",
    repoName: "acme/frontend",
    status: "processing",
    lastActive: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
  {
    id: 3,
    title: "Data pipeline docs",
    repoName: "acme/data-pipeline",
    status: "failed",
    lastActive: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
  {
    id: 4,
    title: "Legacy monolith",
    repoName: "acme/monolith",
    status: "completed",
    lastActive: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
];

export default {
  title: "Components/Session/SessionSidebar",
  component: SessionSidebar,
  args: {
    onToggle: fn(),
    onSelectSession: fn(),
    onNewSession: fn(),
  },
};

export const Default = {
  args: { sessions: SESSIONS },
};

export const Empty = {
  args: { sessions: [] },
};
