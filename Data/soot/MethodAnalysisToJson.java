/**  MethodAnalysisToJson.java */

import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import soot.*;
import soot.jimple.IfStmt;
import soot.jimple.LookupSwitchStmt;
import soot.jimple.TableSwitchStmt;
import soot.options.Options;
import soot.toolkits.graph.Block;
import soot.toolkits.graph.BlockGraph;
import soot.toolkits.graph.BriefBlockGraph;
import soot.toolkits.graph.ExceptionalBlockGraph;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

class DependencyInfo {
   String name;     // - 클래스명 또는 “Class#method(param…)”
   String body;     // 원본 메서드/클래스 소스 (없으면 "(source not found)")
}

/** POJO → Gson 직렬화 */
class MethodInfo {
   String clazz;
   String methodName;
   String signature;
   String visibility;   // ★ 추가
   String body;
   int nodes;
   int edges;
   int cc;
   List<String> flowSummary;
   List<String> blockList;   // B0 { … }  형태의 블록 의사코드
   List<String> blockEdges;  // “B0 --> B1” 형태의 엣지 목록
   List<DependencyInfo> depClasses  = new ArrayList<>();
   List<DependencyInfo> depMethods  = new ArrayList<>();

}

public class MethodAnalysisToJson {

   /* ====== 사용자 환경 설정 ====== */
   private static final String CLASSES_PATH =
             //input your project target\\classes path            
           "C:\\Users\\.....\\target\\classes";

   private static final Path SOURCE_ROOT = Path.of(
           "C:\\Users\\....\\target\\classes");
            //input your project target\\classes path  
   private static final String JSON_OUT =
             //input your data save path
           "C:/Users/..../all_methods.json";

   private static boolean isEligible(SootClass c, SootMethod m) {
       if (!c.isPublic() || c.isInterface() || c.isAbstract() || c.getName().contains("$")) return false;
       // (1) 바디 없는 메서드는 제외
       if (!m.isConcrete()) return false;

       // (2) 생성자/클래스 초기화자 제외
       if (m.isConstructor() || m.isStaticInitializer()) return false;

       // (3) 컴파일러 생성 메서드 제외 (synthetic, bridge)
       final int ACC_BRIDGE    = 0x0040;
       final int ACC_SYNTHETIC = 0x1000;
       int mod = m.getModifiers();

       return (mod & ACC_BRIDGE) == 0 && (mod & ACC_SYNTHETIC) == 0;
   }

       private static String toSimpleSig(String sootSubSig) {
           int p = sootSubSig.indexOf(' ');
           String rest = sootSubSig.substring(p + 1);            // "doX(java.util.List,java.lang.String)"
           String name = rest.substring(0, rest.indexOf('('));   // "doX"
           String params = rest.substring(rest.indexOf('(') + 1, rest.lastIndexOf(')'));
           if (params.isBlank()) return name + "()";
           String simple = Arrays.stream(params.split(","))
                   .map(s -> s.substring(s.lastIndexOf('.') + 1)) // 패키지 제거
                   .reduce((a,b) -> a + "," + b).orElse("");
           return name + "(" + simple + ")";
       }


       private static String norm(String t) {
           t = t.trim();
           // 배열 · var-args 제거
           while (t.endsWith("[]") || t.endsWith("..."))
               t = t.substring(0, t.lastIndexOf('[') > 0 ? t.lastIndexOf('[') : t.lastIndexOf('.'));
           // 제네릭 제거
           int g = t.indexOf('<');
           if (g >= 0) t = t.substring(0, g);
           return t.substring(t.lastIndexOf('.') + 1);
       }


       private static List<String> sootParts(String sub) {
           int sp = sub.indexOf(' ');
           String rest = sub.substring(sp + 1);                 // foo(java.lang.String[])
           String name = rest.substring(0, rest.indexOf('('));
           String[] ps = rest.substring(rest.indexOf('(') + 1, rest.lastIndexOf(')')).split(",");
           List<String> out = new ArrayList<>();
           out.add(name);
           for (String p : ps) if (!p.isBlank()) out.add(norm(p));
           return out;
       }

       private static boolean matches(MethodDeclaration src, SootMethod sm) {
           if (!src.getNameAsString().equals(sm.getName())) return false;
           if (src.getParameters().size() != sm.getParameterCount()) return false;

           List<String> soot = sootParts(sm.getSubSignature());
           for (int i = 0; i < src.getParameters().size(); i++) {
               String srcTy  = norm(src.getParameter(i).getType().asString());
               String sootTy = soot.get(i + 1);
               if (!srcTy.equalsIgnoreCase(sootTy)) return false;
           }
           return true;
       }

       public static void main(String[] args) throws Exception {


           G.reset();
           Options.v().set_prepend_classpath(true);
           Options.v().set_allow_phantom_refs(true);
           Options.v().set_process_dir(Collections.singletonList(CLASSES_PATH));
           Options.v().set_output_format(Options.output_format_none);
           Options.v().set_soot_classpath(String.join(
                   File.pathSeparator,
                   CLASSES_PATH,
                   System.getProperty("java.class.path")));
           Scene.v().loadNecessaryClasses();


           Map<String, Path> sourceIndex = new HashMap<>();
           Files.walk(SOURCE_ROOT)
                   .filter(p -> p.toString().endsWith(".java"))
                   .forEach(p -> {
                       String simple = p.getFileName().toString().replace(".java", "");
                       sourceIndex.putIfAbsent(simple, p);
                   });


           List<MethodInfo> result = new ArrayList<>();
           Map<String, CompilationUnit> cuCache = new HashMap<>(); // 클래스별 JavaParser 캐시


           for (SootClass sc : new ArrayList<>(Scene.v().getApplicationClasses())) {

               for (SootMethod sm : new ArrayList<>(sc.getMethods())) { // ★ 변경!
                   if (!isEligible(sc, sm)) continue;

                   Body body;
                   try { body = sm.retrieveActiveBody(); }
                   catch (Exception ex) { continue; }

                   // ── CFG & 복잡도
                   BlockGraph cfg = new ExceptionalBlockGraph(body);
                   int nodes = cfg.size();
                   int edges = cfg.getBlocks().stream().mapToInt(b -> cfg.getSuccsOf(b).size()).sum();
                   int cc    = edges - nodes + 2;
                   if (nodes == 0 || edges == 0) continue;                     


                   int startLine = Integer.MAX_VALUE;
                   int endLine = Integer.MIN_VALUE;

                   for (Unit unit : body.getUnits()) {
                       int line = unit.getJavaSourceStartLineNumber();
                       if (line > 0) {
                           startLine = Math.min(startLine, line);
                           endLine = Math.max(endLine, line);
                       }
                   }

                   // ── Flow Summary
                   List<String> flow = new ArrayList<>();
                   for (Block blk : cfg) {
                       List<Block> succs = cfg.getSuccsOf(blk);
                       if (succs.size() < 2) continue;
                       Unit tail = blk.getTail();
                       String cond;
                       if (tail instanceof IfStmt)
                           cond = ((IfStmt) tail).getCondition().toString();
                       else if (tail instanceof LookupSwitchStmt || tail instanceof TableSwitchStmt)
                           cond = "switch-on " + tail.getUseBoxes().get(0).getValue();
                       else
                           continue;
                       flow.add(String.format("B%d : If(%s) → B%d | else → B%d",
                               blk.getIndexInMethod(), cond,
                               succs.get(0).getIndexInMethod(), succs.get(1).getIndexInMethod()));
                   }

                   // ── JavaParser: 메서드 바디 & 시그니처
                   String fqn = sc.getName();
                   CompilationUnit cu = cuCache.computeIfAbsent(fqn, k -> {
                       try {
                           Path p = SOURCE_ROOT.resolve(k.replace('.', '/') + ".java");
                           return StaticJavaParser.parse(Files.readString(p));
                       } catch (Exception e) { return null; }
                   });
                   String bodySrc = "(source not found)";
                   String sootSub = sm.getSubSignature();               // 패키지 포함
                   String sootSimple = toSimpleSig(sootSub);            // 패키지 제거 버전
                   if (cu != null) {
                       Optional<ClassOrInterfaceDeclaration> cd =
                               cu.getClassByName(sc.getShortName());
                       if (cd.isPresent()) {
                           Optional<MethodDeclaration> md = cd.get().getMethods().stream()
                                   .filter(m -> matches(m, sm))   // ← 여기!
                                   .findFirst();
                           if (md.isPresent())
                               bodySrc = md.get().getBody().map(Object::toString).orElse("(no body)");
                       }
                   }

                   if ("(source not found)".equals(bodySrc) && startLine < endLine) {
                       try {
                           Path src = SOURCE_ROOT.resolve(fqn.replace('.', '/') + ".java");
                           List<String> lines = Files.readAllLines(src);
                           bodySrc = String.join(System.lineSeparator(),
                                   lines.subList(startLine - 1, Math.min(endLine, lines.size())));
                       } catch (Exception ignore) { /* 실패 시 그대로 둠 */ }
                   }

                   Map<String,List<String>> pretty = buildPrettyCFG(body);

                   Set<String>              classDeps       = new HashSet<>();
                   Set<List<String>>        selfMethodDeps  = new HashSet<>();
                   ClassOrInterfaceDeclaration cdAst        = null;   // 현재 클래스 AST

                   if (cu != null) {
                       Optional<ClassOrInterfaceDeclaration> optCd =
                               cu.getClassByName(sc.getShortName());
                       if (optCd.isPresent()) {
                           cdAst = optCd.get();
                           // 현재 처리 중 메서드의 AST
                           optCd.get().getMethods().stream()
                                   .filter(m -> matches(m, sm))
                                   .findFirst()
                                   .ifPresent(md -> {
                                       String pkg = sc.getPackageName();
                                       classDeps.addAll(findInternalClassDeps(md, pkg));
                                       selfMethodDeps.addAll(findSelfMethodDeps(md));
                                   });
                       }
                   }




                   MethodInfo mi = new MethodInfo();
   
                   for (String clsSimpleOrFqn : classDeps) {

                       String simple = clsSimpleOrFqn.contains(".")
                               ? clsSimpleOrFqn.substring(clsSimpleOrFqn.lastIndexOf('.')+1)
                               : clsSimpleOrFqn;

                       // ① 동일 패키지 FQN 시도
                       String fqnDep = clsSimpleOrFqn.contains(".")
                               ? clsSimpleOrFqn
                               : sc.getPackageName() + "." + simple;

                       Path srcPath  = SOURCE_ROOT.resolve(fqnDep.replace('.', '/') + ".java");
                       if (!Files.exists(srcPath))                 // ② 존재 안 하면 전역 인덱스 탐색
                           srcPath = sourceIndex.get(simple);

                       DependencyInfo di = new DependencyInfo();
                       di.name = fqnDep.contains(".") ? fqnDep : simple;          // 최소한 이름은 기록
                       CompilationUnit depCu = loadCU(srcPath, cuCache);
                       di.body = depCu != null
                               ? depCu.toString()
                               : "(source not found)";
                       mi.depClasses.add(di);
                   }


                   for (List<String> sig : selfMethodDeps) {
                       String mName   = sig.get(0);
                       int    arity   = Integer.parseInt(sig.get(1));

                       DependencyInfo di = new DependencyInfo();
                       di.name = sc.getShortName() + "#" + mName + "(..." + arity + ")";

                       String bodyTxt = "(source not found)";

                       // ① 현재 클래스 CD 우선
                       if (cdAst != null) {
                           bodyTxt = findMethodBodySrc(cdAst, mName,
                                   Collections.nCopies(arity, ""));
                       }

       
                       if ("(source not found)".equals(bodyTxt)) {
                           Path clsPath = sourceIndex.get(sc.getShortName());
                           CompilationUnit altCu = loadCU(clsPath, cuCache);
                           if (altCu != null) {
                               Optional<ClassOrInterfaceDeclaration> altCd =
                                       altCu.getClassByName(sc.getShortName());
                               if (altCd.isPresent()) {
                                   bodyTxt = findMethodBodySrc(
                                           altCd.get(), mName,
                                           Collections.nCopies(arity, ""));
                               }
                           }
                       }

                       di.body = bodyTxt;
                       mi.depMethods.add(di);
                   }


                   mi.clazz       = fqn;
                   mi.methodName  = sm.getName();
                   mi.signature   = sm.getSubSignature();
                   mi.visibility  = vis(sm);
                   mi.body        = bodySrc;
                   mi.nodes       = nodes;
                   mi.edges       = edges;
                   mi.cc          = cc;
                   mi.flowSummary = flow;
                   mi.blockList   = pretty.get("blocks");   // ★
                   mi.blockEdges  = pretty.get("edges");    // ★
                   result.add(mi);
               }
           }


           Gson gson = new GsonBuilder().setPrettyPrinting().create();
           try (FileWriter fw = new FileWriter(JSON_OUT)) {
               gson.toJson(result, fw);
           }
           System.out.println("✅ 완료: " + JSON_OUT + " 에 " + result.size() + "개 메서드 정보를 저장했습니다.");
       }


       private static Map<String, List<String>> buildPrettyCFG(Body body) {

           BlockGraph cfg = new BriefBlockGraph(body);

           Map<Unit,Integer> u2b = new HashMap<>();
           for (Block b : cfg) for (Unit u : b) u2b.put(u, b.getIndexInMethod());

           List<String> blocks = new ArrayList<>();
           List<String> edges  = new ArrayList<>();

           for (Block b : cfg) {
               StringBuilder sb = new StringBuilder();
               sb.append("B").append(b.getIndexInMethod()).append(" {");

               for (Unit u : b) {
                   String out = pseudo(u, b, cfg, u2b);   // ← 아래 헬퍼 재사용
                   sb.append("\n  ").append(out);
               }
               sb.append("\n}");
               blocks.add(sb.toString());

               if (cfg.getSuccsOf(b).isEmpty()) {
                   edges.add("B"+b.getIndexInMethod()+" --> [EXIT]");
               } else {
                   for (Block s : cfg.getSuccsOf(b)) {
                       edges.add("B"+b.getIndexInMethod()+" --> B"+s.getIndexInMethod());
                   }
               }
           }
           Map<String,List<String>> m = new HashMap<>();
           m.put("blocks", blocks);
           m.put("edges",  edges);
           return m;
       }



       private static String invoke2pseudo(soot.jimple.InvokeExpr ie) {


           if (ie instanceof soot.jimple.SpecialInvokeExpr sie &&
                   ie.getMethodRef().name().equals("<init>")) {
               String cls = sie.getBase().getType().toString();
               cls = cls.substring(cls.lastIndexOf('.') + 1);
               String args = argList(ie);
               return "new " + cls + "(" + args + ")";
           }

           if (ie instanceof soot.jimple.StaticInvokeExpr) {
               String cls = ie.getMethodRef().declaringClass().getName();
               cls = cls.substring(cls.lastIndexOf('.') + 1);
               return cls + "." + ie.getMethodRef().name() + "(" + argList(ie) + ")";
           }


           if (ie instanceof soot.jimple.InstanceInvokeExpr iie) {
               String base = strip(iie.getBase().toString());
               return base + "." + ie.getMethodRef().name() + "(" + argList(ie) + ")";
           }


           return "dynInvoke " + ie.getMethodRef().name() + "(" + argList(ie) + ")";
       }


       private static String argList(soot.jimple.InvokeExpr ie) {
           return ie.getArgs().isEmpty()
                   ? ""
                   : ie.getArgs().toString().replace("[", "").replace("]", "");
       }

       private static String strip(String s) {
           if (s.startsWith("@this:"))       return "this";
           if (s.startsWith("@parameter"))   return "param" + s.charAt(10);
           int p = s.lastIndexOf('.');
           return p >= 0 ? s.substring(p+1) : s;
       }


       private static String pseudo(Unit u,
                                    Block curBlk,
                                    BlockGraph cfg,
                                    Map<Unit,Integer> unit2Block) {

           if (u instanceof soot.jimple.AssignStmt as) {
               String lhs = strip(as.getLeftOp().toString());
               String rhs = as.containsInvokeExpr()
                       ? invoke2pseudo(as.getInvokeExpr())
                       : strip(as.getRightOp().toString());
               return lhs + " = " + rhs;
           }

           if (u instanceof soot.jimple.IfStmt is) {
               List<Block> succs = cfg.getSuccsOf(curBlk);       // [true, false]
               if (succs.size() == 2) {
                   int trueBid  = succs.get(0).getIndexInMethod();
                   int falseBid = succs.get(1).getIndexInMethod();
                   return String.format("if (%s) goto B%d else B%d",
                           strip(is.getCondition().toString()),
                           trueBid, falseBid);
               }
               return "if (" + strip(is.getCondition().toString()) + ") …";
           }


           if (u instanceof soot.jimple.GotoStmt gs) {
               return "goto B" + unit2Block.get(gs.getTarget());
           }

           if (u instanceof soot.jimple.ReturnStmt ||
                   u instanceof soot.jimple.ReturnVoidStmt) {
               return "return";
           }
           if (u instanceof soot.jimple.ThrowStmt ts) {
               return "throw " + strip(ts.getOp().toString());
           }


           if (u instanceof soot.jimple.InvokeStmt ivs) {
               return invoke2pseudo(ivs.getInvokeExpr());
           }


           return strip(u.toString());
       }

       private static String vis(SootMethod m) {
           if (m.isPublic())    return "public";
           if (m.isProtected()) return "protected";
           if (m.isPrivate())   return "private";
           return "package";
       }

       /** MethodDeclaration → 내부에서 사용/호출된 동일-패키지 클래스 이름 집합 */
       private static Set<String> findInternalClassDeps(MethodDeclaration md, String pkg) {
           Set<String> set = new HashSet<>();
           md.findAll(com.github.javaparser.ast.type.ClassOrInterfaceType.class)
                   .stream()
                   .map(t -> t.getNameWithScope())
                   .filter(n -> n.contains(".") && n.startsWith(pkg))   // 같은 패키지
                   .forEach(set::add);
           return set;
       }

       private static Set<List<String>> findSelfMethodDeps(MethodDeclaration md) {
           Set<List<String>> deps = new HashSet<>();
           md.findAll(com.github.javaparser.ast.expr.MethodCallExpr.class)
                   .stream()
                   // this.x()  또는  x()  만 집계
                   .filter(mc -> !mc.getScope().isPresent() || mc.getScope().get().isThisExpr())
                   .forEach(mc -> {
                       List<String> sig = new ArrayList<>();
                       sig.add(mc.getNameAsString());          // 0: 메서드 이름
                       sig.add(String.valueOf(mc.getArguments().size())); // 1: 파라미터 개수만 기록
                       deps.add(sig);                          // 예: ["internalCalc","2"]
                   });
           return deps;
       }

       private static String findMethodBodySrc(ClassOrInterfaceDeclaration cd,
                                               String mName,
                                               List<String> dummyParamList) {

           int arity = dummyParamList.size();

           return cd.getMethods().stream()
                   .filter(m -> m.getNameAsString().equals(mName)
                           && m.getParameters().size() == arity)
                   .findFirst()
                   .flatMap(m -> m.getBody().map(Object::toString))
                   .orElse("(source not found)");
       }


       private static CompilationUnit loadCU(Path p,
                                             Map<String, CompilationUnit> cuCache) {
           if (p == null) return null;
           return cuCache.computeIfAbsent(p.toString(), k -> {          // key = 절대경로
               try {
                   return StaticJavaParser.parse(Files.readString(p));
               } catch (Exception e) { return null; }
           });
       }

   }

