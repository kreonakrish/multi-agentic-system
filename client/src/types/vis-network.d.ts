declare module 'vis-network' {
  export class Network {
    constructor(
      container: HTMLElement,
      data: { nodes: any; edges: any },
      options?: any
    );
    on(event: string, callback: (params: any) => void): void;
    destroy(): void;
  }
} 