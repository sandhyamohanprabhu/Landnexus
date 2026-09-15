import { createServer } from 'vite';

process.stdout.on('error', (err) => {
  if (err.code === 'EPIPE') return;
});
process.stderr.on('error', (err) => {
  if (err.code === 'EPIPE') return;
});
process.on('uncaughtException', (err) => {
  if (err.code === 'EPIPE') return;
  console.error(err);
});
process.on('unhandledRejection', (err) => {
  console.error(err);
});

async function start() {
  const server = await createServer({
    server: {
      port: 5173,
      host: '127.0.0.1'
    }
  });
  await server.listen();
  server.printUrls();
  setInterval(() => {}, 60000);
}

start();
