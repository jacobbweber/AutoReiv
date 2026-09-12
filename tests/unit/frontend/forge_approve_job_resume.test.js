import { describe, expect, it } from 'vitest';
import {
  forgeApproveResumesSameJob,
  shouldPreventOrphanMint,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-251 Forge Approve same job_id', () => {
  it('forgeApproveResumesSameJob accepts resumed same job payload', () => {
    expect(
      forgeApproveResumesSameJob({
        job_id: 'job_abc',
        session_id: 'sess_1',
        resumed: true,
        same_job: true,
        orphan: false,
        soft_deleted: false,
      }),
    ).toBe(true);
  });

  it('rejects orphan or soft-delete payloads', () => {
    expect(
      forgeApproveResumesSameJob({
        job_id: 'job_abc',
        resumed: true,
        orphan: true,
      }),
    ).toBe(false);
    expect(
      forgeApproveResumesSameJob({
        job_id: 'job_abc',
        resumed: true,
        soft_deleted: true,
      }),
    ).toBe(false);
    expect(forgeApproveResumesSameJob({ resumed: true })).toBe(false);
  });

  it('shouldPreventOrphanMint when waiting_approval and not resume', () => {
    expect(shouldPreventOrphanMint({ openJobStatus: 'waiting_approval', resume: false })).toBe(true);
    expect(shouldPreventOrphanMint({ openJobStatus: 'waiting_approval', resume: true })).toBe(false);
    expect(shouldPreventOrphanMint({ openJobStatus: 'running', resume: false })).toBe(false);
  });
});
