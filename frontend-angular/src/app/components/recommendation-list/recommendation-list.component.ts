import { Component, input } from '@angular/core';
import { StrainCardComponent } from '../strain-card/strain-card.component';
import { StrainItem } from '../../models/strain.interface';

@Component({
  selector: 'app-recommendation-list',
  standalone: true,
  imports: [StrainCardComponent],
  templateUrl: './recommendation-list.component.html',
  styleUrl: './recommendation-list.component.scss',
})
export class RecommendationListComponent {
  readonly strains = input<StrainItem[]>([]);
}
