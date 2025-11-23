import Header from "./Header";

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      <Header />
      <main className="pt-20 px-4 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
};

export default Layout;
