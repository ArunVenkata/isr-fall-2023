import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subject, debounceTime, takeUntil } from 'rxjs';
import { SearchService } from '../search.service';
import { NzNotificationService } from 'ng-zorro-antd/notification';

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.scss']
})
export class HomeComponent implements OnInit, OnDestroy {
  isLoading: boolean = false;
  searchChange$: Subject<string> = new Subject();
  searchResults: any[] = [];
  private ngUnsubscribe$ = new Subject();
  
  constructor(private searchService: SearchService, private nzNotificationService: NzNotificationService) {
  }

  ngOnInit(): void {
    this.searchChange$.asObservable().pipe(takeUntil(this.ngUnsubscribe$)).pipe(debounceTime(700)).subscribe((text:string) => {
      console.log(text);
      this.loadSearchResults(text);
    })
  }
  ngOnDestroy(): void {
    this.ngUnsubscribe$.next(true);
    this.ngUnsubscribe$.complete()
  }

  loadSearchResults(searchText: string){
    this.isLoading = true;
    this.searchService.getSearchResults(searchText).pipe(takeUntil(this.ngUnsubscribe$)).subscribe((resp: any) => {
        console.log(resp)
        this.isLoading =false;
        if(!resp.success){
          this.nzNotificationService.warning("An error Occurred", resp.message || "")
          return 
        }
        
        
        this.searchResults = resp.data

    }, (err) => {
      console.log("ERR", err)
    } )
  }
  onSearchChange(searchText: string){
    this.isLoading = true;
    if(searchText === ""){
      this.searchResults = []
      this.isLoading=false;
      return
    }
    this.searchChange$.next(searchText);
  }
}
