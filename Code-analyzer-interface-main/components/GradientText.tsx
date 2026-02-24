
import React from 'react';

interface GradientTextProps {
  children: React.ReactNode;
  className?: string;
  as?: React.ElementType;
}

const GradientText: React.FC<GradientTextProps> = ({ children, className = '', as: Component = 'span' }) => {
  return (
    <Component className={`bg-gradient-to-r from-accent-primary to-accent-secondary text-transparent bg-clip-text ${className}`}>
      {children}
    </Component>
  );
};

export default GradientText;
