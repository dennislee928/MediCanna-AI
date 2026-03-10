import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

interface RuntimeConfig {
  gatewayUrl?: string;
}

const DEFAULT_GATEWAY_URL = 'http://localhost:8080/api/v1/recommend';

@Injectable({ providedIn: 'root' })
export class RuntimeConfigService {
  private gatewayUrl = DEFAULT_GATEWAY_URL;

  constructor(private http: HttpClient) {}

  async load(): Promise<void> {
    try {
      const config = await firstValueFrom(
        this.http.get<RuntimeConfig>('assets/app-config.json'),
      );
      if (config?.gatewayUrl?.trim()) {
        this.gatewayUrl = config.gatewayUrl.trim();
      }
    } catch {
      this.gatewayUrl = DEFAULT_GATEWAY_URL;
    }
  }

  getGatewayUrl(): string {
    return this.gatewayUrl;
  }
}
