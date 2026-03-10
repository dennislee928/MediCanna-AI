import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RecommendationResponse } from '../models/strain.interface';
import { RuntimeConfigService } from '../config/runtime-config.service';

export interface RecommendRequest {
  symptoms: string;
  avoid_effects: string[];
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(
    private http: HttpClient,
    private runtimeConfig: RuntimeConfigService,
  ) {}

  getRecommendations(body: RecommendRequest): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(this.runtimeConfig.getGatewayUrl(), body);
  }
}
