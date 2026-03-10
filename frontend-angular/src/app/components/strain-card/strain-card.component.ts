import { Component, input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { StrainItem } from '../../models/strain.interface';

@Component({
  selector: 'app-strain-card',
  standalone: true,
  imports: [MatCardModule, MatChipsModule, DecimalPipe],
  templateUrl: './strain-card.component.html',
  styleUrl: './strain-card.component.scss',
})
export class StrainCardComponent {
  readonly strain = input.required<StrainItem>();
}
