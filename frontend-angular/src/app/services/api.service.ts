import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RecommendationResponse } from '../models/strain.interface';

const GATEWAY_URL = 'http://localhost:8080/api/v1/recommend';

export interface RecommendRequest {
  symptoms: string;
  avoid_effects: string[];
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  constructor(private http: HttpClient) {}

  getRecommendations(body: RecommendRequest): Observable<RecommendationResponse> {
    return this.http.post<RecommendationResponse>(GATEWAY_URL, body);
  }
}
