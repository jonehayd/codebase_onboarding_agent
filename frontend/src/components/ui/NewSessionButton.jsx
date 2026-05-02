import { FaPlus } from "react-icons/fa6";

export default function NewSessionButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full py-3 text-text bg-surface-raised text-lg cursor-pointer border border-border hover:bg-surface-highest transition-colors duration-150"
    >
      <FaPlus className="inline-block mr-4" />
      New Session
    </button>
  );
}
