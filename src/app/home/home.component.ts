import { Component } from '@angular/core';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css'
})
export class HomeComponent {

  downloadPDF() {
    const link = document.createElement('a');
    link.href = '../../assets/Logica.pdf';
    link.download = 'Logica.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
