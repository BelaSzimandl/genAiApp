import { Octokit } from "@octokit/rest";
import { Repo } from "../types/github";

export class RepoManager {
    private octokit: Octokit;

    constructor(authToken: string) {
        this.octokit = new Octokit({ auth: authToken });
    }

    async createRepo(repoName: string, isPrivate: boolean = false): Promise<Repo> {
        const response = await this.octokit.repos.createForAuthenticatedUser({
            name: repoName,
            private: isPrivate,
        });
        return response.data;
    }

    async listRepos(): Promise<Repo[]> {
        const response = await this.octokit.repos.listForAuthenticatedUser();
        return response.data;
    }

    async deleteRepo(owner: string, repoName: string): Promise<void> {
        await this.octokit.repos.delete({
            owner,
            repo: repoName,
        });
    }
}