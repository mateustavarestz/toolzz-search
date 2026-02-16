import React from 'react';
import { Loader2 } from 'lucide-react';
import { motion, HTMLMotionProps } from 'framer-motion';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'dark';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
}

type CombinedProps = ButtonProps & HTMLMotionProps<"button">;

const variantClasses: Record<string, string> = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    danger: 'btn-danger',
    dark: 'btn-dark',
};

const sizeClasses: Record<string, string> = {
    sm: 'btn-sm',
    md: '',
    lg: 'btn-lg',
};

export const Button = React.forwardRef<HTMLButtonElement, CombinedProps>(
    ({ className = '', variant = 'primary', size = 'md', loading, children, disabled, ...props }, ref) => {
        const classes = [
            'btn',
            variantClasses[variant] || '',
            sizeClasses[size] || '',
            className,
        ].filter(Boolean).join(' ');

        return (
            <motion.button
                whileTap={{ scale: 0.96 }}
                className={classes}
                ref={ref}
                disabled={disabled || loading}
                {...props}
            >
                {loading && <Loader2 size={16} className="animate-spin" />}
                {children}
            </motion.button>
        );
    }
);
Button.displayName = "Button";
