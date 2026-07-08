export interface Repo {
    id: number;
    name: string;
    full_name: string;
    owner: {
        login: string;
        id: number;
        avatar_url: string;
        url: string;
    };
    private: boolean;
    html_url: string;
    description: string | null;
    created_at: string;
    updated_at: string;
    pushed_at: string;
    language: string | null;
    forks_count: number;
    stargazers_count: number;
    watchers_count: number;
    open_issues_count: number;
    default_branch: string;
}

export interface WebhookPayload {
    action: string;
    repository: Repo;
    sender: {
        login: string;
        id: number;
        avatar_url: string;
        url: string;
    };
    // Additional fields can be added based on the specific webhook event
}