import { prisma } from '../db';
import { analyzeCheck } from './claude';
import { CheckFormData } from '../types';
import { logger } from '../logger';

interface ListChecksParams {
  userId: string;
  page: number;
  limit: number;
  filter?: string;
  search?: string;
}

export async function listChecks({ userId, page, limit, filter, search }: ListChecksParams) {
  const where: Record<string, unknown> = { userId };

  if (filter && ['LOW', 'MEDIUM', 'HIGH'].includes(filter)) {
    where.result = { path: ['overall'], equals: filter };
  }

  if (search) {
    where.counterparty = { contains: search, mode: 'insensitive' };
  }

  const [data, total] = await Promise.all([
    prisma.check.findMany({
      where,
      orderBy: { createdAt: 'desc' },
      skip: (page - 1) * limit,
      take: limit,
    }),
    prisma.check.count({ where }),
  ]);

  return { data, total, page, hasMore: page * limit < total };
}

export async function getCheck(id: string, userId: string) {
  const check = await prisma.check.findFirst({ where: { id, userId } });
  if (!check) return null;
  return check;
}

export async function createCheck(userId: string, formData: CheckFormData) {
  logger.info({ userId, counterparty: formData.cp }, 'Creating check');

  const result = await analyzeCheck(formData);

  const check = await prisma.check.create({
    data: {
      userId,
      counterparty: formData.cp,
      country: formData.country,
      product: formData.product,
      currency: formData.currency ?? '',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formData: formData as any,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      result: result as any,
    },
  });

  return check;
}

export async function deleteCheck(id: string, userId: string): Promise<boolean> {
  const check = await prisma.check.findFirst({ where: { id, userId } });
  if (!check) return false;
  await prisma.check.delete({ where: { id } });
  return true;
}

export function buildCSV(checks: Awaited<ReturnType<typeof listChecks>>['data']): string {
  const header = ['ID', 'Дата', 'Контрагент', 'Страна', 'Товар', 'Вердикт', 'Риск-скор', 'Уровень'];
  const rows = checks.map((c) => {
    const r = c.result as Record<string, unknown> | null;
    return [
      c.id,
      c.createdAt.toISOString(),
      c.counterparty,
      c.country,
      c.product,
      String(r?.verdict ?? ''),
      String(r?.score ?? ''),
      String(r?.overall ?? ''),
    ];
  });

  const escape = (v: string) => `"${v.replace(/"/g, '""')}"`;
  return [header, ...rows].map((r) => r.map(escape).join(',')).join('\n');
}
