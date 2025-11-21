import React from "react";

const Input = ({ className = "", ...props }) => {
  const baseClasses =
    "border border-slate-200 dark:border-slate-600 rounded-md px-3 py-2 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100";

  return <input className={`${baseClasses} ${className}`} {...props} />;
};

export default Input;
