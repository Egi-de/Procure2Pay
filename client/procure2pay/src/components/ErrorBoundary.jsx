import React from "react";
import PropTypes from "prop-types";
import Button from "./Button";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorInfo: null };
  }

  // eslint-disable-next-line no-unused-vars
  static getDerivedStateFromError(_error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      errorInfo: errorInfo,
    });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-md w-full space-y-8">
            <div>
              <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
                Something went wrong
              </h2>
              <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
                An unexpected error occurred. Please try again.
              </p>
            </div>
            <div className="flex justify-center">
              <Button onClick={this.handleRetry} variant="primary">
                Try Again
              </Button>
            </div>
            {import.meta.env.MODE === "development" && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400">
                  Error Details (Development Only)
                </summary>
                <pre className="mt-2 text-xs text-red-600 dark:text-red-400 whitespace-pre-wrap">
                  {this.state.errorInfo?.componentStack ||
                    "No stack trace available"}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node,
};

export default ErrorBoundary;
