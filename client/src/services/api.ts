const API_BASE_URL = '/api';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

export class ApiService {
  protected async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('API GET error:', error);
      return { error: error instanceof Error ? error.message : 'Unknown error occurred' };
    }
  }

  protected async post<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('API POST error:', error);
      return { error: error instanceof Error ? error.message : 'Unknown error occurred' };
    }
  }

  protected async put<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('API PUT error:', error);
      return { error: error instanceof Error ? error.message : 'Unknown error occurred' };
    }
  }

  protected async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return { data };
    } catch (error) {
      console.error('API DELETE error:', error);
      return { error: error instanceof Error ? error.message : 'Unknown error occurred' };
    }
  }
}

export const api = new ApiService(); 