// components/layout/Panel.jsx
// Generic resizable panel. Renders a 1px drag handle on the specified side.
// The resize calculation logic lives in the parent (AppLayout).

export default function Panel({
  width,
  side = "right",
  onDragStart,
  children,
  className = "",
}) {
  const handlePos = side === "left" ? "left-0" : "right-0";

  return (
    <div className={`relative flex-none h-full ${className}`} style={{ width }}>
      <div className="h-full overflow-hidden">{children}</div>
      {onDragStart && (
        <div
          className={`absolute top-0 ${handlePos} w-1 h-full cursor-col-resize z-20
            hover:bg-white/20 active:bg-white/30 transition-colors`}
          onMouseDown={onDragStart}
        />
      )}
    </div>
  );
}
