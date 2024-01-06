import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class SearchService {

  constructor(private httpClient: HttpClient) { }


  getSearchResults(searchText:string){
    return this.httpClient.get("http://localhost:5000/search", {
      params: {
        search: searchText
      }
    })
  }
}
