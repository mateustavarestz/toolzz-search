import React from 'react';
import { ChevronDown } from 'lucide-react';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
    options?: { label: string; value: string }[];
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
    ({ className = '', label, error, children, options, id, ...props }, ref) => {
        const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="form-group">
                {label && (
                    <label htmlFor={selectId}>
                        {label}
                    </label>
                )}
                <div className="relative">
                    <select
                        id={selectId}
                        className={`${error ? 'input-error' : ''} ${className}`}
                        style={{ paddingRight: '36px', appearance: 'none' }}
                        ref={ref}
                        {...props}
                    >
                        {options ? options.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                        )) : children}
                    </select>
                    <div className="pointer-events-none absolute" style={{ right: '12px', top: '50%', transform: 'translateY(-50%)' }}>
                        <ChevronDown size={16} color="var(--text-tertiary)" />
                    </div>
                </div>
                {error && <p className="form-error">{error}</p>}
            </div>
        );
    }
);
Select.displayName = "Select";
