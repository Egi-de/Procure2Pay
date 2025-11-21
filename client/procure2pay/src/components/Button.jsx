import React from "react";

const Button = ({ variant = "primary", onClick, children, ...props }) => {
  const baseClasses = "px-4 py-2 rounded-md font-medium transition-colors";

  const variants = {
    primary:
      "bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600",
    success:
      "bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-100 dark:hover:bg-emerald-500/30",
    danger:
      "bg-rose-100 text-rose-700 hover:bg-rose-200 dark:bg-rose-500/20 dark:text-rose-100 dark:hover:bg-rose-500/30",
    link: "text-blue-600 hover:underline dark:text-blue-300",
  };

  return (
    <button
      className={`${baseClasses} ${variants[variant] || variants.primary}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
