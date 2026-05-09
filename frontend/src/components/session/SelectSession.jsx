import { RiTerminalBoxFill } from "react-icons/ri";

export default function SelectSession() {
  return (
    <div className="flex flex-col items-center px-5 justify-center h-screen">
      <RiTerminalBoxFill className="w-20 h-20 text-color-text m-4 p-2 border border-border bg-surface-high" />
      <h1 className="text-2xl mt-6 mb-2">Select a Session</h1>
      <p className="color-text-muted text-center max-w-80">
        No session is currently active. Select one from the history or
        initialize a new repository scan to begin.
      </p>
      <button className="py-2 px-20 bg-text text-black font-medium text-lg cursor-pointer hover:bg-text-muted transition-colors duration-150 mt-6">
        INITIALIZE NEW SECTION
      </button>
    </div>
  );
}
