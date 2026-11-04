import type { Category } from '../../api/types.ts'
import { CATEGORY_LABELS } from './categories.ts'

interface Props {
  value: Category
  onChange: (category: Category) => void
  label?: string
}

export default function CategoryPicker({ value, onChange, label = 'Categoría' }: Props) {
  return (
    <div className="segmented" role="radiogroup" aria-label={label}>
      {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
        <button
          key={category}
          type="button"
          role="radio"
          aria-checked={value === category}
          className={value === category ? 'selected' : ''}
          onClick={() => onChange(category)}
        >
          {CATEGORY_LABELS[category]}
        </button>
      ))}
    </div>
  )
}
