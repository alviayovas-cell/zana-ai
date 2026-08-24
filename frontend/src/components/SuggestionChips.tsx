import type { SuggestionItem } from '../types/chat';
import './SuggestionChips.css';

interface Props {
  suggestions: SuggestionItem[];
  onSelect: (suggestion: SuggestionItem) => void;
  disabled?: boolean;
}

export function SuggestionChips({ suggestions, onSelect, disabled }: Props) {
  if (!suggestions.length) return null;

  return (
    <div className="suggestion-chips" role="list" aria-label="Quick replies">
      {suggestions.map((s, i) => (
        <button
          key={`${s.action_type}-${i}`}
          role="listitem"
          className="chip"
          onClick={() => onSelect(s)}
          disabled={disabled}
          aria-label={`Quick reply: ${s.label}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}
