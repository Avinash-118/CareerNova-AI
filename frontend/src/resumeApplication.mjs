// Normalize both dataset and live-result links before opening the assistant.
export function applicationJob(job) {
  const url = [job.apply_url, job.url].find(value => {
    try {
      const parsed = new URL(value);
      return ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password;
    } catch { return false; }
  });
  return url ? {...job, apply_url:url, title:job.title || job.job_title || 'Selected role'} : null;
}
