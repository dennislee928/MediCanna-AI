/** 與 Rust Gateway 回傳對齊的品種結構 */
export interface StrainItem {
  name: string;
  type: string;
  rating: number;
  effects: string;
  flavor: string;
}

export interface ResponseMeta {
  request_id: string;
  model_version: string;
  warnings: string[];
}

export interface RecommendationResponse {
  recommendations: StrainItem[];
  meta: ResponseMeta;
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
  };
}
