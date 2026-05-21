import 'dotenv/config';
import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import { pinoHttp } from 'pino-http';
import { config } from './config';
import { logger } from './logger';
import { prisma } from './db';
import { apiLimiter } from './middleware/rateLimit';
import authRoutes from './routes/auth';
import checksRoutes from './routes/checks';
import usersRoutes from './routes/users';

const app = express();

app.set('trust proxy', 1);

app.use(cors({ origin: config.CORS_ORIGIN, credentials: true }));
app.use(express.json({ limit: '1mb' }));
app.use(pinoHttp({ logger }));
app.use('/api', apiLimiter);

app.get('/health', (_req: Request, res: Response) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api/auth', authRoutes);
app.use('/api/checks', checksRoutes);
app.use('/api/users', usersRoutes);

app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: 'Not found' });
});

app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
  logger.error(err, 'Unhandled error');
  res.status(500).json({ error: 'Internal server error' });
});

async function main() {
  await prisma.$connect();
  logger.info('Database connected');

  app.listen(config.PORT, () => {
    logger.info({ port: config.PORT, env: config.NODE_ENV }, 'Aegis Comply API started');
  });
}

main().catch((err) => {
  logger.error(err, 'Failed to start server');
  process.exit(1);
});

process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  await prisma.$disconnect();
  process.exit(0);
});
