import express from 'express';
import bodyParser from 'body-parser';
import { AuthManager } from './github/auth';
import { RepoManager } from './github/repos';
import { WebhookManager } from './github/webhooks';

const app = express();
const port = process.env.PORT || 3000;

app.use(bodyParser.json());

const authManager = new AuthManager();
const repoManager = new RepoManager();
const webhookManager = new WebhookManager();

app.post('/auth', async (req, res) => {
    try {
        const { code } = req.body;
        const token = await authManager.getAccessToken(code);
        res.json({ token });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/repos', async (req, res) => {
    try {
        const { name } = req.body;
        const repo = await repoManager.createRepo(name);
        res.json(repo);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/repos', async (req, res) => {
    try {
        const repos = await repoManager.listRepos();
        res.json(repos);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.delete('/repos/:name', async (req, res) => {
    try {
        const { name } = req.params;
        await repoManager.deleteRepo(name);
        res.status(204).send();
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/webhook', (req, res) => {
    webhookManager.handleWebhook(req.body);
    res.status(200).send();
});

app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});