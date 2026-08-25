import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
  hoverable?: boolean;
  glow?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  onClick,
  hoverable = false,
  glow = false,
}) => {
  return (
    <div
      onClick={onClick}
      className={`
        bg-[#111827]/80 backdrop-blur-md rounded-xl border border-slate-800/80 p-5
        ${glow ? 'shadow-glow border-indigo-500/30' : 'shadow-md'}
        ${hoverable ? 'cursor-pointer hover:border-slate-700 hover:bg-[#161F30] transition-all duration-200' : ''}
        ${className}
      `}
    >
      {children}
    </div>
  );
};
