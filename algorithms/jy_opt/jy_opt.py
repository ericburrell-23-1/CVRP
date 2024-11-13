


class node:
	def __init__(self,cust,capRem):
		self.cust=cust #or depot
		self.capRem=capRem
		self.pred_edges=dict()
		self.succ_edges=dict()



class edge:
	def __init__(self,pred_node,succ_node):
		self.b_to_valid=set()
		self.pred_node=pred_node
		self.succ_node=succ_node
		self.my_uv_edge=None

	def add_coresp(self,my_uv_edge):
		self.my_uv_edge=my_uv_edge

class uv_edge:
	def __init__(self,u,v,my_cost,dictRCIName2Nhat):
		self.u=u
		self.v=v
		self.cost=my_cost
		self.dict_con_name_2_coeff=dict()
		self.dict_con_name_2_coeff[u]=-1
		for RCI_name in dictRCIName2Nhat:
			if  u in RCI_name and v not in RCI_name:
				self.dict_con_name_2_coeff[RCI_name]=-1
	
class jy_Opt_formulator:
	"""Basic class using no-LA neighbors or LA arcs"""
	def compute_succ(self,u,d,v):
		value=d-self.demandDict[u]
		lst=self.myDem_list[v]
		filtered_values = [x for x in lst if x <= value]
		return max(filtered_values) if filtered_values else -1
		
	def update_uv_edge_info(self):
		if self.dict_uv_2_uv_edge==None:
			for u in self.NPlus:
				for v in self.NPlus:
					my_uv_edge=uv_edge(u,v,self.cost_uv[u,v],self.myRCI)
					my_uv_name=tuple([u,v])
					self.dict_uv_2_uv_edge[my_uv_name]=my_uv_edge

	def make_nodes(self):
		self.my_nodes=dict()
		source_node=node(-1,self.capacity)
		source_node_name=tuple([-1,self.capacity])
		self.my_nodes[source_node_name]=source_node

		sink_node=node(-2,0)
		sink_node_name=tuple([-2,0])
		self.my_nodes[sink_node_name]=sink_node
	
		for u in self.N:
			for d in self.myDem_list[u]:
				new_node=node(u,d)
				new_node_name=tuple([u,d])
				self.my_nodes[new_node_name]=new_node

	def make_source_sink_edges(self):
		for u in self.N:
			#source connection
			n1_id=tuple([-1,self.capacity])
			n2_id=tuple([u,self.myDem_list[u][-1]])
			edge_tuple=[n1_id[0],n1_id[1],n2_id[0],n2_id[1]]
			
			n1=self.my_nodes[n1_id]
			n2=self.my_nodes[n2_id]
			new_edge=edge(n1,n2)
			n1.addSucc(new_edge)
			n2.addPrev(new_edge)
			self.my_edges[edge_tuple]=new_edge
			
			
			####sink connection
			
			n1_id=tuple([u,self.myDem_list[u][0]])
			n2_id=tuple([-2,0])

			edge_tuple=[n1_id[0],n1_id[1],n2_id[0],n2_id[1]]
			
			n1=self.my_nodes[n1_id]
			n2=self.my_nodes[n2_id]
			new_edge=edge(n1,n2)
			n1.addSucc(new_edge)
			n2.addPrev(new_edge)
			self.my_edges[edge_tuple]=new_edge
	
	def make_sucessor_edges(self):
		for u in self.N:
			#connections from d to next one 
			for di in range(0,len(self.myDem_list[u]-1)):#myDem_list[u]:
				
				n1_id=tuple([u,self.myDem_list[u][di+1]])
				n1=self.my_nodes[n1_id]

				
				n2_id=tuple([u,self.myDem_list[u][di]])
				n2=self.my_nodes[n2_id]
				
				n1.addSucc(new_edge)
				n2.addPrev(new_edge)
				new_edge=edge(n1,n2)
				edge_tuple=tuple([u,self.myDem_list[u][di+1],u,self.myDem_list[u][di]])
				self.my_edges[edge_tuple]=new_edge
	
	def create_non_dom_edges(self):
		for (u,v) in self.myN2:
			for di in range(0,len(self.myDem_list[u])):#myDem_list[u]:
				d=self.myDem_list[u][d]
				d_out_1=self.compute_succ(self,u,d,v)
				d2b=-1
				if di>0:
					d2=self.myDem_list[u][d-1]
					d_out_2=self.compute_succ(self,u,d2,v)
				if d_out_1>d_out_2:
					n1_id=tuple([u,d])
					n2_id=tuple([v,d_out_1])
					n1=self.my_nodes[n1_id]
					n2=self.my_nodes[n2_id]
					new_edge=edge(n1,n2)
					n1.addSucc(new_edge)
					n2.addPrev(new_edge)
					edge_tuple=tuple([u,d,v,d_out_1])
					self.my_edges[edge_tuple]=new_edge
				

	def make_edges_for_l(self):
		self.my_edges_l=dict()

		for b in range(0,len(self.myBetaList)):
			self.my_edges_l[b]=set([])
			beta=self.myBetaList[b]
			for e in self.my_edges:
				if beta[e.prev_node]<=beta[e.succ_node]:
					e.b_to_valid.add(b)
					self.my_edges_l[beta].add(e)	
					
	def make_edge_coresp(self):
		for e in self.my_edges:
			u=e.prev_node.cust
			v=e.succ_node.cust
			
			e.add_coresp(self.dict_uv_2_uv_edge[u,v])

	def make_LP_dictionary(self):
		self.objective=[] # DICTIONARY?
		
		for b in range(0,len(self.myBetaList)):
			for e in self.my_edges_l[b]:
				self.objective[tuple([e,b])]=e.my_uv_edge.cost
		
		self.RHS=dict()
		# COVER CONSTRS
		for u in self.N:
			con_name=tuple(u)
			self.RHS[con_name]=-1 # SHOULD BE POSITIVE 1?

		# RCI CONSTRS
		for nhat in self.myRCI:
			con_name=tuple(nhat)
			self.RHS[con_name]=self.myRCI[nhat]
		
		self.edge_con_name_2_val=dict()
		for n in self.my_nodes:	
			if n.cust>-0.5: #not the depot
				for b in range(0,len(self.myBetaList)):
					con_name=tuple([n,b])
					self.RHS[con_name]=self.myRCI[nhat] # CONFUSED WHAT THIS IS, SHOULDN'T RHS BE 0? IF THIS IS FLOW CONSTRAINT
					for e in n.pred_edges:
						if b in e.b_to_valid:
							edge_name=tuple([e,b])
							self.edge_con_name_2_val[tuple([con_name,edge_name])]=-1 # THIS LOOKS LIKE FLOW IN CONSTRAINT

					for e in n.succ_edges:
							edge_name=tuple([e,b])
							self.edge_con_name_2_val[tuple([con_name,edge_name])]=1 # AND FLOW OUT
		
		for e in self.my_edges:
			for b in range(0,len(self.myBetaList)):
				if b in e.b_to_valid:
					edge_name=tuple([e,b])
					for con_name in e.my_uv_edge.dict_con_name_2_coeff:
						self.edge_con_name_2_val[tuple([con_name,edge_name])]=e.my_uv_edge.dict_con_name_2_coeff[con_name]
		
		
	def __init__(self,NPlus,N,myDem_list,myBetaList,myN2,myRCI,demandDict,dict_uv_2_uv_edge,cost_uv,capacity):
		
		
		#NPlus:  list of all custoemrs plus -1,-2 (soruce,sink)
		#N:  list of all customers
		#myDem_list is a dictionary of sorted lists:  myNodes[u] is a list of all nodes of the form (u,d) for some d.  
		#myBetaList:  dictionary of beta terms where myBetaList[l][u] provides beta^l_u
		#myN2:  is a set of uv transfers allowed
		#demandDict: mapping from NPlus to demand of the customer (zero for depot) 
		#cost_uv:  dictionary cost to go from u to v
		#capacity:  vehicle capacity
		#myRCI:  is a dictionary where domain is list of customers and output is the RHS for the constraint 
		#DONT USE NmyLANeighbors:  is a dictionary where for a given u it has a list of la neighbors for u
		#DONT USE Dictionary[u]:   u,N_p,v where N_p is sorted list my name of intermediate customers has lowest cost.  
		#DONT USE myClippedLAarcCosts:  For any given u
		
		self.NPlus=NPlus
		self.N=N
		self.myDem_list=myDem_list
		self.myBetaList=myBetaList
		self.myN2=myN2
		self.myRCI=myRCI
		self.demandDict=demandDict
		self.dict_uv_2_uv_edge=dict_uv_2_uv_edge
		self.cost_uv=cost_uv
		self.capacity=capacity
		
		self.update_uv_edge_info()
		
		self.make_nodes()
		
		self.my_edges = {}
		self.make_source_sink_edges()
		self.make_successor_edges()
		self.create_non_dom_edges()
		self.make_edge_coresp()
		self.make_edges_for_l()
		
		
		self.make_LP_dictionary()
