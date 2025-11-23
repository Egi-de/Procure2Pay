# TODO: Procure2Pay Project Refinements

## Deployment (Critical - Missing for Full Satisfaction)

- [ ] Deploy to public environment (AWS EC2, Render, Fly.io, Railway, DigitalOcean, or VPS)
- [ ] Update README.md with public URL/IP
- [ ] Ensure both backend and frontend are accessible via public domain
- [ ] Configure production environment variables (secrets, domains)
- [ ] Set up SSL/TLS certificates
- [ ] Test public instance functionality

## Testing & Validation (Recommended Improvements)

- [ ] Expand server/requests/tests.py with comprehensive test cases:
  - Workflow transitions (pending → approved/rejected)
  - Permission checks for all roles
  - Document processing accuracy
  - Concurrent approval handling
- [ ] Add frontend integration tests (e.g., Cypress or Playwright)
- [ ] Test document processing with real proforma/receipt samples
- [ ] Validate email notifications (approval/rejection)

## Document Processing Enhancements (Optional)

- [ ] Improve extract_proforma_metadata regex patterns for better accuracy
- [ ] Add OpenAI API integration for more intelligent data extraction
- [ ] Enhance PO generation with better formatting/templates
- [ ] Add support for more document formats (DOCX, etc.)

## Performance & Security (Optional)

- [ ] Add pagination to API endpoints for large datasets
- [ ] Implement caching (Redis) for frequently accessed data
- [ ] Add rate limiting to API endpoints
- [ ] Security audit: CSRF, XSS, SQL injection checks
- [ ] Add API versioning

## UI/UX Improvements (Optional)

- [ ] Add loading states and better error handling in frontend
- [ ] Implement real-time notifications (WebSockets or polling)
- [ ] Add search/filter functionality beyond status
- [ ] Mobile responsiveness improvements
- [ ] Accessibility (ARIA labels, keyboard navigation)

## Monitoring & DevOps (Optional)

- [ ] Add logging and monitoring (Sentry, etc.)
- [ ] Set up automated backups for database
- [ ] Add health check endpoints
- [ ] Improve CI/CD pipeline (deploy on merge to main)
