import { Router, Request, Response } from 'express';
import { z } from 'zod';
import { requireAuth } from '../middleware/auth';
import { validate } from '../middleware/validate';
import { checkLimiter } from '../middleware/rateLimit';
import { listChecks, getCheck, createCheck, deleteCheck, buildCSV } from '../services/checks';
import { logger } from '../logger';

const router = Router();

router.use(requireAuth);

const createCheckSchema = z.object({
  cp: z.string().min(1, 'Counterparty is required'),
  country: z.string().min(1, 'Country is required'),
  product: z.string().min(1, 'Product is required'),
  ctype: z.string().optional(),
  reg: z.string().optional(),
  tnved: z.string().optional(),
  dual: z.string().optional(),
  enduse: z.string().optional(),
  ubo: z.string().optional(),
  uboCountry: z.string().optional(),
  ownership: z.string().optional(),
  currency: z.string().optional(),
  val: z.string().optional(),
  bank: z.string().optional(),
  payMethod: z.string().optional(),
  transit: z.string().optional(),
  vessel: z.string().optional(),
  finalDest: z.string().optional(),
});

router.get('/', async (req: Request, res: Response): Promise<void> => {
  const page = Math.max(1, parseInt(Array.isArray(req.query.page) ? String(req.query.page[0]) : String(req.query.page ?? '1')));
  const limit = Math.min(100, Math.max(1, parseInt(Array.isArray(req.query.limit) ? String(req.query.limit[0]) : String(req.query.limit ?? '20'))));
  const filter = Array.isArray(req.query.filter) ? String(req.query.filter[0]) : String(req.query.filter ?? '');
  const search = Array.isArray(req.query.search) ? String(req.query.search[0]) : String(req.query.search ?? '');

  try {
    const result = await listChecks({
      userId: req.user!.id,
      page,
      limit,
      filter: filter || undefined,
      search: search || undefined,
    });
    res.json(result);
  } catch (err) {
    logger.error(err, 'Failed to list checks');
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/export/csv', async (req: Request, res: Response): Promise<void> => {
  try {
    const result = await listChecks({ userId: req.user!.id, page: 1, limit: 1000 });
    const csv = buildCSV(result.data as Parameters<typeof buildCSV>[0]);
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="aegis_checks.csv"');
    res.send('﻿' + csv);
  } catch (err) {
    logger.error(err, 'Failed to export CSV');
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const check = await getCheck(String(req.params.id), req.user!.id);
    if (!check) {
      res.status(404).json({ error: 'Check not found' });
      return;
    }
    res.json(check);
  } catch (err) {
    logger.error(err, 'Failed to get check');
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.post('/', checkLimiter, validate(createCheckSchema), async (req: Request, res: Response): Promise<void> => {
  try {
    const check = await createCheck(req.user!.id, req.body);
    res.status(201).json(check);
  } catch (err) {
    logger.error(err, 'Failed to create check');
    if (err instanceof Error && err.message.includes('Claude')) {
      res.status(502).json({ error: 'AI analysis service unavailable, please try again' });
      return;
    }
    res.status(500).json({ error: 'Internal server error' });
  }
});

router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const deleted = await deleteCheck(String(req.params.id), req.user!.id);
    if (!deleted) {
      res.status(404).json({ error: 'Check not found' });
      return;
    }
    res.status(204).send();
  } catch (err) {
    logger.error(err, 'Failed to delete check');
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;
