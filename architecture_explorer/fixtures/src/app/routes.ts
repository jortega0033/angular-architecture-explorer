import { HomeComponent } from './home';
export const routes = [
  { path: '', component: HomeComponent },
  { path: 'jobs', loadChildren: () => import('./jobs') },
];
