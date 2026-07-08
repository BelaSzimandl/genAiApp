import { Octokit } from "@octokit/rest";

export class AuthManager {
    private octokit: Octokit;

    constructor(private clientId: string, private clientSecret: string) {
        this.octokit = new Octokit({
            auth: {
                clientId: this.clientId,
                clientSecret: this.clientSecret,
            },
        });
    }

    async authenticateUser(code: string): Promise<string> {
        const response = await this.octokit.request('POST /login/oauth/access_token', {
            headers: {
                accept: 'application/json',
            },
            data: {
                client_id: this.clientId,
                client_secret: this.clientSecret,
                code,
            },
        });
        return response.data.access_token;
    }

    async getAccessToken(code: string): Promise<string> {
        return this.authenticateUser(code);
    }
}