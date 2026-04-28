import React from 'react';

type ButtonVariant = 'primary';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary:
    'bg-blue-600 text-white hover:bg-blue-700 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
};

const BASE_CLASSES =
  'inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none';

const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  type = 'button',
  className = '',
  children,
  ...rest
}) => (
  <button
    type={type}
    className={`${BASE_CLASSES} ${VARIANT_CLASSES[variant]} ${className}`.trim()}
    {...rest}
  >
    {children}
  </button>
);

export default Button;
