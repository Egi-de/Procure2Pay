import Header from "./Header";

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Header />
      <main className="pt-16">{children}</main>
    </div>
  );
};

export default Layout;
