import pickle
import numpy as np

class node:
	def __init__(self,cust,capRem):
		self.cust=cust #or depot
		self.capRem=capRem
		self.pred_edges=dict()
		self.succ_edges=dict()#dict()
	def addSucc(self,edge_tuple,new_edge):
		#self.succ_edges[].append(new_edge)
		self.succ_edges[edge_tuple]=new_edge
	def addPrev(self,edge_tuple,new_edge):
		#self.pred_edges.append(new_edge)
		self.pred_edges[edge_tuple]=new_edge


class edge:
	def __init__(self,pred_node,succ_node,my_tup_name):
		self.b_to_valid=set()
		self.pred_node=pred_node
		self.succ_node=succ_node
		self.my_uv_edge=None
		self.my_tup_name=my_tup_name

	def add_coresp(self,my_uv_edge):
		self.my_uv_edge=my_uv_edge

class uv_edge:
	def __init__(self,u,v,my_cost,dictRCIName2Nhat):
		self.u=u
		self.v=v
		self.cost=my_cost
		self.dict_con_name_2_coeff=dict()
		self.dict_con_name_2_coeff['Cover',u]=1
		for RCI_name in dictRCIName2Nhat:
			if  u in RCI_name and v not in RCI_name:
				con_name=tuple(['RCI',RCI_name])
				self.dict_con_name_2_coeff[con_name]=1
	
class jy_Opt_formulator:
	"""Basic class using no-LA neighbors or LA arcs"""
	def compute_succ(self,u,d,v):
		value=d-self.demandDict[u]
		lst=self.myDem_list.get(v, [])
		filtered_values = [x for x in lst if x <= value]
		return max(filtered_values) if filtered_values else -1
		
	def update_uv_edge_info(self):
		
		if len(self.dict_uv_2_uv_edge)==0:
			for u in self.NPlus:
				for v in self.NPlus:
					if u!=v and (u!=-1 or v!=-2) and (u!=-2) and (v!=-1):
						my_uv_edge=uv_edge(u,v,self.cost_uv[u,v],self.myRCI)
						my_uv_name=tuple([u,v])
						self.dict_uv_2_uv_edge[my_uv_name]=my_uv_edge
					elif u == v:
						my_uv_edge=uv_edge(u,v,0,self.myRCI)
						my_uv_edge.dict_con_name_2_coeff['Cover',u]=0
						my_uv_name=tuple([u,v])
						self.dict_uv_2_uv_edge[my_uv_name]=my_uv_edge

					#else:
					#	print('u,v')
					#	print([u,v])
						
		
	def make_nodes(self):
		self.my_nodes=dict()
		source_node=node(-1,self.capacity)
		source_node_name=tuple([-1,self.capacity])
		self.my_nodes[source_node_name]=source_node

		sink_node=node(-2,0)
		sink_node_name=tuple([-2,0])
		self.my_nodes[sink_node_name]=sink_node
		
		# print('self.N')
		# print(self.N)
		for u in self.N:
			for d in self.myDem_list[u]:
				new_node=node(u,d)
				new_node_name=tuple([u,d])
				self.my_nodes[new_node_name]=new_node

	def make_source_sink_edges(self):
		for u in self.N:
			#source connection
			n1_id=tuple([-1,self.capacity])
			n2_id=tuple([u,self.myDem_list[u][0]])
			edge_tuple=tuple([n1_id[0],n1_id[1],n2_id[0],n2_id[1]])
			
			n1=self.my_nodes[n1_id]
			n2=self.my_nodes[n2_id]
			new_edge=edge(n1,n2,edge_tuple)

			n1.addSucc(edge_tuple,new_edge)
			n2.addPrev(edge_tuple,new_edge)
			self.my_edges[edge_tuple]=new_edge

			# print(f"Added edge: {edge_tuple}")
			
			
			####sink connection
			
			n1_id=tuple([u,self.myDem_list[u][-1]])
			n2_id=tuple([-2,0])

			edge_tuple=tuple([n1_id[0],n1_id[1],n2_id[0],n2_id[1]])
			# print(f"Added edge: {edge_tuple}")
			
			n1=self.my_nodes[n1_id]
			n2=self.my_nodes[n2_id]
			new_edge=edge(n1,n2,edge_tuple)
			n1.addSucc(edge_tuple,new_edge)
			n2.addPrev(edge_tuple,new_edge)
			self.my_edges[edge_tuple]=new_edge
	
	def make_successor_edges(self):
		for u in self.N:
			#connections from d to next one 
			for di in range(0,len(self.myDem_list[u])-1):#myDem_list[u]:
				
				n1_id=tuple([u,self.myDem_list[u][di+1]])
				n1=self.my_nodes[n1_id]

				
				n2_id=tuple([u,self.myDem_list[u][di]])
				n2=self.my_nodes[n2_id]
				
				
				edge_tuple=tuple([u,self.myDem_list[u][di+1],u,self.myDem_list[u][di]])
				new_edge=edge(n1,n2,edge_tuple)
				self.my_edges[edge_tuple]=new_edge
				n1.addSucc(edge_tuple,new_edge)
				n2.addPrev(edge_tuple,new_edge)
	def create_non_dom_edges(self):
		for (u,v) in self.myN2:
			for di in range(0,len(self.myDem_list[u])):#myDem_list[u]:
				d=self.myDem_list[u][di]
				d_out_1=self.compute_succ(u,d,v)
				d_out_2=-1
				if di>0:
					d2=self.myDem_list[u][di-1]
					d_out_2=self.compute_succ(u,d2,v)
				if d_out_1>d_out_2:
					n1_id=tuple([u,d])
					n2_id=tuple([v,d_out_1])
					n1=self.my_nodes[n1_id]
					n2=self.my_nodes[n2_id]
					edge_tuple=tuple([u,d,v,d_out_1])

					new_edge=edge(n1,n2,edge_tuple)

					n1.addSucc(edge_tuple,new_edge)
					n2.addPrev(edge_tuple,new_edge)
					self.my_edges[edge_tuple]=new_edge
				

	def make_edges_for_l(self):
		self.my_edges_l=dict()

		for b in range(0,len(self.myBetaList)):
			self.my_edges_l[b]=set([])
			beta=self.myBetaList[b]
			for e in self.my_edges:
				my_e=self.my_edges[e]
				if beta.index(my_e.pred_node.cust)<=beta.index(my_e.succ_node.cust):
					my_e.b_to_valid.add(b)
					self.my_edges_l[b].add(my_e)	
					
	def make_edge_coresp(self):
		for e in self.my_edges:
			u=self.my_edges[e].pred_node.cust
			v=self.my_edges[e].succ_node.cust
			#print('self.dict_uv_2_uv_edge')
			#print(self.dict_uv_2_uv_edge)
			tmp=self.dict_uv_2_uv_edge[u,v]
			self.my_edges[e].add_coresp(tmp)

	def make_LP_dictionary(self):
		self.objective=dict() 
		
		for bi in range(0,len(self.myBetaList)):
			for e in self.my_edges_l[bi]:
				ei=e.my_tup_name
				self.objective[tuple([ei,bi])]=e.my_uv_edge.cost
		
		self.RHS=dict()
		# COVER CONSTRS
		for u in self.N:
			con_name=tuple(['Cover',u])
			self.RHS[con_name]=1 

		# RCI CONSTRS
		for nhat in self.myRCI:
			con_name=tuple(['RCI',nhat])
			self.RHS[con_name]=self.myRCI[nhat]
		
		self.edge_con_name_2_val=dict()
		for ni in self.my_nodes:	
			n=self.my_nodes[ni]
			if n.cust>-0.5: #not the depot
				for bi in range(0,len(self.myBetaList)):
					node_name = tuple([ni,bi])
					con_name=tuple(['Flow',node_name]) #tuple([ni,bi])
					self.RHS[con_name]=0#tuple(['Flow',ni]) # CONFUSED WHAT THIS IS, SHOULDN'T RHS BE 0? IF THIS IS FLOW CONSTRAINT

					# FLOW IN
					for ei in n.pred_edges:
						e=n.pred_edges[ei]
						if bi in e.b_to_valid:
							
							edge_name=tuple([ei,bi])
							self.edge_con_name_2_val[tuple([con_name,edge_name])]=1

					# FLOW OUT
					for ei in n.succ_edges:
						e=n.succ_edges[ei]
						if bi in e.b_to_valid:
							#e=n.pred_edges[ei]
							edge_name=tuple([ei,bi])
							self.edge_con_name_2_val[tuple([con_name,edge_name])]=-1
		
		for ei in self.my_edges:
			e=self.my_edges[ei]
			for bi in range(0,len(self.myBetaList)):
				if bi in e.b_to_valid:
					edge_name=tuple([ei,bi])
					for con_name in e.my_uv_edge.dict_con_name_2_coeff:
						self.edge_con_name_2_val[tuple([con_name,edge_name])]=e.my_uv_edge.dict_con_name_2_coeff[con_name]
		
		
	def pre_process(self):
		
		#print('myN2')
		#print(myN2)
		#input('--')
		#print('self.NPlus')
		#print(self.NPlus)
		new_N=[]#dict()#self.NPlus
		
		for u_in in self.N:
			u=int(u_in)-1
			new_N.append(u)#[u]=self.NPlus[u_in]
		self.N=new_N
		new_N_Plus=[]#dict()#self.NPlus
		
		for u_in in self.NPlus:
			u=int(u_in)
			if u>0.5:
				u=u-1
			new_N_Plus.append(u)#[u]=self.NPlus[u_in]
		self.NPlus=new_N_Plus
		
		#print('self.myDem_list')
		#print(self.myDem_list)
		new_dem_list=dict()
		
		for u_in in self.myDem_list:
			u=int(u_in)
			if u>0.5:
				u=u-1
			new_dem_list[u]=self.myDem_list[u_in]
		self.myDem_list=new_dem_list
		self.myDem_list[-1]=[0]
		self.myDem_list[-2]=[0]
		
		
		#print('myBetaList')
		#print(myBetaList)
		for l_ind_term in self.myBetaList:
			tmp=self.myBetaList[l_ind_term].copy()
			for i in range(1,len(self.myBetaList[l_ind_term])-1):
				tmp[i]=int(tmp[i])
				if tmp[i]>0.5:
					tmp[i]=tmp[i]-1
			self.myBetaList[l_ind_term]=tmp
		#print('myBetaList')
		#print(myBetaList)
		#print('self.myN2')
		#print(self.myN2)
		#print(type)
		my_new_n2=set()
		for  new_pair in self.myN2:
			u=new_pair[0]
			v=new_pair[1]
			u1=int(u)
			v1=int(v)
			if u1>0.5:
				u1=u1-1
			if v1>0.5:
				v1=v1-1
			new_term=tuple([u1,v1])
			my_new_n2.add(new_term)
		self.myN2=my_new_n2
		
		new_RCI=dict()
		for this_rci in self.myRCI:
			#print('----')
			#print(this_rci)
			##print(type(this_rci))
			my_copy_rci=[]
			for k in range(0,len(this_rci)):
				my_copy_rci.append(int(this_rci[k])-1)
			my_copy_rci=tuple(my_copy_rci)
			new_RCI[my_copy_rci]=self.myRCI[this_rci]
		
		my_new_dem_dict=dict()
		for u_in in self.demandDict:
			u=int(u_in)
			if u>0.5:
				u=u-1
			my_new_dem_dict[u]=self.demandDict[u_in]
		self.demandDict=my_new_dem_dict
		
		new_cost_uv=dict()
		for my_in in self.cost_uv:
			u=my_in[0]
			v=my_in[1]
			u1=int(u)
			v1=int(v)
			if u1>0.5:
				u1=u1-1
			if v1>0.5:
				v1=v1-1
			new_tup=tuple([u1,v1])
			new_cost_uv[new_tup]=self.cost_uv[my_in]
		
		new_terms_add=dict()
		for in_tup in new_cost_uv:
			u=in_tup[0]
			v=in_tup[1]
			if tuple([v,u]) not in new_cost_uv:
				new_terms_add[tuple([v,u])]=new_cost_uv[in_tup]
				#new_cost_uv[tuple([v,u])]=new_cost_uv[tuple([u,v])]
		for my_tup in new_terms_add:
			new_cost_uv[my_tup]=new_terms_add[my_tup]
		self.cost_uv=new_cost_uv
		#print('self.cost_uv')
		#print(self.cost_uv)
			#print(my_copy_rci)
			#input('---')
		#for u_in in self.myDem_list
		#input('done pre')
	def __init__(self,N,NPlus,myDem_list,myBetaList,myN2,myRCI,demandDict,dict_uv_2_uv_edge,cost_uv,capacity):
		
		
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
		
		# self.pre_process() # Customer IDs are already adjusted before starting
		
		self.update_uv_edge_info()
		
		self.make_nodes()
		
		self.my_edges = {}
		self.make_source_sink_edges()
		self.make_successor_edges()
		self.create_non_dom_edges()
		self.make_edge_coresp()
		self.make_edges_for_l()
		
		
		self.make_LP_dictionary()

		# for node_name in self.my_nodes:
		# 	print(f"Node: {node_name}")



# loaded_outputs=[]
# # Save the outputs to a file
# print('jy_inputs_4.pkl')
# with open('jy_inputs_4.pkl', 'rb') as f:
#     loaded_outputs = pickle.load(f)
# N=loaded_outputs[1]
# NPlus=loaded_outputs[0]
# myDem_list=loaded_outputs[2]
# myBetaList=loaded_outputs[3]
# myN2=loaded_outputs[4]
# myRCI=loaded_outputs[5]
# demandDict=loaded_outputs[6]
# dict_uv_2_uv_edge=loaded_outputs[7]
# cost_uv=loaded_outputs[8]
# capacity=loaded_outputs[9]
# tmp=jy_Opt_formulator(N,NPlus,myDem_list,myBetaList,myN2,myRCI,demandDict,dict_uv_2_uv_edge,cost_uv,capacity)
