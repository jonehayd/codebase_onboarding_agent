import { useState } from "react";
import NewSessionModal from "./NewSessionModal";

export default {
  title: "Components/Session/NewSessionModal",
  component: NewSessionModal,
  decorators: [
    (Story) => (
      <div className="bg-base min-h-screen flex items-center justify-center">
        <Story />
      </div>
    ),
  ],
};

// interactive story with open/close toggle
export const Default = {
  render: () => {
    const [isOpen, setIsOpen] = useState(true);
    const [submitted, setSubmitted] = useState(null);

    return (
      <div>
        <button
          onClick={() => setIsOpen(true)}
          className="px-4 py-2 bg-surface-raised border border-border text-text text-sm rounded cursor-pointer hover:bg-surface-high transition-colors"
        >
          Open Modal
        </button>

        {submitted && (
          <div className="mt-4 p-4 bg-surface-raised border border-border rounded text-sm text-text-muted font-mono">
            Submitted: {JSON.stringify(submitted, null, 2)}
          </div>
        )}

        <NewSessionModal
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          onSubmit={(data) => {
            setSubmitted(data);
            setIsOpen(false);
          }}
        />
      </div>
    );
  },
};

// always open, no close handler — for static inspection
export const AlwaysOpen = {
  args: {
    isOpen: true,
    onClose: () => {},
    onSubmit: () => {},
  },
};

export const Closed = {
  args: {
    isOpen: false,
    onClose: () => {},
    onSubmit: () => {},
  },
};
