import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    hint?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    ({ className = '', label, error, hint, id, ...props }, ref) => {
        const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="form-group">
                {label && (
                    <label htmlFor={inputId}>
                        {label}
                    </label>
                )}
                <input
                    id={inputId}
                    className={`${error ? 'input-error' : ''} ${className}`}
                    ref={ref}
                    aria-invalid={error ? 'true' : undefined}
                    aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
                    {...props}
                />
                {error && <p id={`${inputId}-error`} className="form-error">{error}</p>}
                {hint && !error && <p id={`${inputId}-hint`} className="form-hint">{hint}</p>}
            </div>
        );
    }
);
Input.displayName = "Input";

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label?: string;
    error?: string;
    hint?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
    ({ className = '', label, error, hint, id, ...props }, ref) => {
        const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="form-group">
                {label && (
                    <label htmlFor={inputId}>
                        {label}
                    </label>
                )}
                <textarea
                    id={inputId}
                    className={`${error ? 'input-error' : ''} ${className}`}
                    ref={ref}
                    aria-invalid={error ? 'true' : undefined}
                    {...props}
                />
                {error && <p className="form-error">{error}</p>}
                {hint && !error && <p className="form-hint">{hint}</p>}
            </div>
        );
    }
);
Textarea.displayName = "Textarea";
