declare module 'vis-data' {
  export class DataSet<T> {
    constructor(data?: T[]);
    add(data: T | T[]): void;
    get(id: string | number): T | null;
    remove(id: string | number): void;
    update(data: T): void;
    clear(): void;
  }
} 