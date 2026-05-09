import SessionEntry from "./SessionEntry";

export default {
  title: "Components/SessionEntry",
  component: SessionEntry,
  argTypes: {
    title: { control: "text" },
    repoName: { control: "text" },
    status: {
      control: "select",
      options: ["completed", "processing", "failed"],
    },
    lastActive: { control: "text" },
    isActive: { control: "boolean" },
  },
  decorators: [
    (Story) => (
      <div className="bg-base p-4 w-72">
        <Story />
      </div>
    ),
  ],
};

export const Default = {
  args: {
    title: "discord_bot",
    repoName: "jonehayd/discord_bot",
    status: "completed",
    lastActive: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    isActive: false,
  },
};

export const Completed = {
  args: {
    title: "discord_bot",
    repoName: "jonehayd/discord_bot",
    status: "completed",
    lastActive: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    isActive: false,
  },
};

export const Processing = {
  args: {
    title: "quickdraw",
    repoName: "jonehayd/multiplayer_quickdraw",
    status: "processing",
    lastActive: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    isActive: false,
  },
};

export const Failed = {
  args: {
    title: "react",
    repoName: "facebook/react",
    status: "failed",
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    isActive: false,
  },
};

export const Active = {
  args: {
    title: "discord_bot",
    repoName: "jonehayd/discord_bot",
    status: "completed",
    lastActive: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    isActive: true,
  },
};

export const LongTitle = {
  args: {
    title: "A very long session title that should truncate",
    repoName: "some-organization/some-very-long-repository-name",
    status: "completed",
    lastActive: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    isActive: false,
  },
};

export const AllStatuses = {
  render: () => (
    <div className="bg-base p-4 w-72 flex flex-col gap-2">
      <SessionEntry
        title="discord_bot"
        repoName="jonehayd/discord_bot"
        status="completed"
        lastActive={new Date(Date.now() - 1000 * 60 * 45).toISOString()}
        isActive={true}
      />
      <SessionEntry
        title="quickdraw"
        repoName="jonehayd/multiplayer_quickdraw"
        status="processing"
        lastActive={new Date(Date.now() - 1000 * 60 * 5).toISOString()}
      />
      <SessionEntry
        title="react"
        repoName="facebook/react"
        status="failed"
        lastActive={new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString()}
      />
    </div>
  ),
};
