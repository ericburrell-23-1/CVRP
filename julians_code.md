# Code Julian Provided for Pricing

```python
def pricing(demand, D, Dist_depot, capacity, N, N_plus , dual):
  G = DiGraph(directed=True, n_res=1)

 # Links between source/sink and customers
  for u in N:
    G.add_edge("Source", str(u), res_cost= array([demand[u]]), weight= Dist_depot[u])
    G.add_edge( str(u), "Sink", res_cost=array([0]), weight=Dist_depot[u]-dual[u])

 # Links between source/sink and customer
  for v in N:
    if v != u:
      G.add_edge(str(u), str(v), res_cost=array([demand[u]]), weight=D[u][v]-dual[u])

  max_res, min_res = [capacity], [0]

  bidirec = BiDirectional(G, max_res, min_res, direction="both", elementary= True)
  bidirec.run()
  str_path=bidirec.path

  int_path=[]
  for sen in str_path:
    if sen != 'Source' and sen != 'Sink':
    sen1=int(sen)
  elif sen == 'Source':
    sen1= -1
  else:
    sen1= -2
  int_path.append(sen1)


  low_pointer=0
  high_pointer=0
  cost_path=0
  while int_path[low_pointer] != -2:
    high_pointer+=1

    if int_path[low_pointer] == -1:
      cost_path+= Dist_depot[int_path[high_pointer]]
    elif int_path[high_pointer] == -2:
      cost_path+= Dist_depot[int_path[low_pointer]]

    if int_path[low_pointer] != -1 and int_path[high_pointer] != -2:
      cost_path+= D[int_path[low_pointer]][int_path[high_pointer]]

    low_pointer+=1



  #Generating columns
  new_column= [0]* len(N)

  for i in N:
    if i in int_path:
      new_column[i]=1

  red_cost=bidirec.total_cost
  result = (new_column,red_cost,cost_path,int_path)

  return result
```
