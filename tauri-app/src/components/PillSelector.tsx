interface PillSelectorProps {
  options: { value: string; label: string }[] | string[];
  value: string | null;
  onChange: (value: string) => void;
}

export function PillSelector({ options, value, onChange }: PillSelectorProps) {
  return (
    <div className="wwk-pills">
      {options.map((opt) => {
        const v = typeof opt === "string" ? opt : opt.value;
        const label = typeof opt === "string" ? opt : opt.label;
        return (
          <button key={v} className={`wwk-pill ${value === v ? "active" : ""}`}
            onClick={() => onChange(v)}>{label}</button>
        );
      })}
    </div>
  );
}
