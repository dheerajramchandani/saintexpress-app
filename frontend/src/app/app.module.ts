import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';

import { SaintSessionComponent } from './components/saint-session/saint-session.component';

@NgModule({
  declarations: [
    SaintSessionComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [SaintSessionComponent]
})
export class AppModule {}
