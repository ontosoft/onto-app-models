import reducer, {initiatePreviewModelList , ServerModelState}  from './serverModelSlice';

test('should return the initial state', () => {
  expect(reducer(undefined, { type: 'unknown' })).toEqual(
    { initiedModelListLoading: false, selectedServerModel: null }
       
  )
})  

test ('should handle initiateInnerModelsListLoading', () => {
    const previousState: ServerModelState = {
      previewModelList: false,
      loadingModelListStatus: 'idle',
      listOfServerModels: [],
      selectedServerModel: null,
      initiedSelectedInnerModelLoading: false,
      innerUIModelLoadingStatus: 'idle',
      innerUIModelLoadingError: null
    };
    expect(
        reducer( previousState, initiatePreviewModelList())
    ).toEqual(
        {initiedModelListLoading: true, selectedServerModel: null}
    )
})