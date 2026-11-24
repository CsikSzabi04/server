# Visual Basic .NET
<!-- tech: vbnet -->
<!-- aliases: visual basic, vb.net, vba -->

A Visual Basic .NET (VB.NET) a .NET platform angol kulcsszavas, olvasható szintaxisú nyelve: ugyanarra a CLR-re és osztálykönyvtárra épül, mint a C#, statikusan típusos (különösen `Option Strict On` mellett), és támogatja az objektumorientált programozást, a generikusokat, a LINQ-t és az async/await-et. Erőssége a gyors üzleti és asztali (WinForms, WPF) alkalmazásfejlesztés, a régi VB6/VBA kódbázisok átemelése, valamint egyedi funkciói, mint az XML literálok és a `Handles` alapú eseménykezelés. A Microsoft már csak karbantartja (új nyelvi funkciók nem jönnek), ezért új projekthez általában a C# az ajánlott; a VBA pedig a VB6-alapú, Office-ba (Excel, Access) épített makrónyelv, ami nem .NET.

## Option Strict, típusok és null-kezelés
<!-- q: Miért kapcsoljam be az Option Strict-et VB.NET-ben, és hogyan kezeljem a típusokat és a nullt? -->
<!-- tags: option strict, option explicit, option infer, types, nullable, type conversion -->

Az `Option Explicit On` kötelezővé teszi a változódeklarációt, az `Option Strict On` tiltja az implicit szűkítő konverziókat és a késői kötést (late binding), így a hibák fordításkor derülnek ki, és a kód gyorsabb. Az `Option Infer On` engedi a `Dim x = 5` típuskikövetkeztetést. Érték típusoknál a `Nullable(Of T)` (`Integer?`) jelzi a hiányzó értéket; a `If(a, b)` kétargumentumos forma a null-coalescing, a `?.` a null-feltételes hozzáférés. Buktató: a `CInt` banker's roundingot használ (`CInt(2.5) = 2`), a `Nothing` értéktípusnál az alapértéket jelenti, és a `=` stringeknél az `Option Compare` beállítástól függ.

```vbnet
Option Strict On
Option Explicit On
Option Infer On

Imports System.Globalization

Module TypesDemo
    Function ParsePrice(input As String) As Decimal?
        ' TryParse: kivétel nélküli konverzió, invariáns kultúrával
        Dim value As Decimal
        If Decimal.TryParse(input, NumberStyles.Number, CultureInfo.InvariantCulture, value) Then
            Return value
        End If
        Return Nothing                       ' Decimal? esetén valódi "nincs érték"
    End Function

    Sub Main()
        Dim count = 42                       ' Option Infer: Integer
        Dim ratio As Double = count / 8      ' a / mindig lebegőpontos osztás
        Dim whole As Integer = count \ 8     ' a \ egész osztás
        ' Dim bad As Integer = ratio         ' Option Strict: fordítási hiba (szűkítés)
        Dim rounded As Integer = CInt(Math.Round(ratio, MidpointRounding.AwayFromZero))

        Console.WriteLine($"{ratio} {whole} {rounded} CInt(2.5)={CInt(2.5)}")   ' 5.25 5 5 CInt(2.5)=2

        Dim price As Decimal? = ParsePrice("12.50")
        Dim missing As Decimal? = ParsePrice("abc")
        Console.WriteLine(If(missing, 0D))                ' null-coalescing → 0
        Console.WriteLine(price.HasValue AndAlso price.Value > 10D)

        ' Rövidzáras logika: AndAlso / OrElse (az And / Or MINDKÉT oldalt kiértékeli!)
        Dim name As String = Nothing
        If name IsNot Nothing AndAlso name.Length > 0 Then Console.WriteLine(name)
        Console.WriteLine(If(name?.Length, -1))          ' null-feltételes hozzáférés
    End Sub
End Module
```

## Osztályok, property-k, öröklés és interfészek
<!-- q: Hogyan írjak osztályokat, öröklést és interfészeket VB.NET-ben? -->
<!-- tags: classes, inheritance, interfaces, properties, mustinherit, overridable, implements -->

A VB.NET osztályai `Class`, az absztrakt osztályok `MustInherit`, az absztrakt tagok `MustOverride`, a felülírható virtuális tagok `Overridable`, a felülírók `Overrides` kulcsszót kapnak. Az interfészt `Implements` köti a taghoz, ami explicit, ezért a metódus neve eltérhet az interfészétől. Az auto-property (`Public Property Name As String`) és a `ReadOnly Property` a C# megfelelőivel azonos, a konstruktor neve `Sub New`. Buktató: a `Shadows` elrejti az ősosztály tagját (nem polimorf), és a `MyBase.New` hívásnak a konstruktor első utasításának kell lennie.

```vbnet
Option Strict On

Public Interface IShippable
    Function ShippingCost() As Decimal
End Interface

Public MustInherit Class Product
    Implements IComparable(Of Product)

    Public ReadOnly Property Sku As String
    Public Property Price As Decimal

    Protected Sub New(sku As String, price As Decimal)
        If String.IsNullOrWhiteSpace(sku) Then Throw New ArgumentException("SKU kötelező", NameOf(sku))
        Me.Sku = sku
        Me.Price = price
    End Sub

    Public MustOverride ReadOnly Property Category As String

    Public Overridable Function Describe() As String
        Return $"{Category} {Sku}: {Price:N0} Ft"
    End Function

    ' Explicit interfész-implementáció: a név szabadon választható
    Public Function CompareByPrice(other As Product) As Integer Implements IComparable(Of Product).CompareTo
        Return Price.CompareTo(other.Price)
    End Function
End Class

Public NotInheritable Class Book
    Inherits Product
    Implements IShippable

    Public Property WeightKg As Decimal

    Public Sub New(sku As String, price As Decimal, weightKg As Decimal)
        MyBase.New(sku, price)               ' kötelezően az első utasítás
        Me.WeightKg = weightKg
    End Sub

    Public Overrides ReadOnly Property Category As String = "Könyv"

    Public Function ShippingCost() As Decimal Implements IShippable.ShippingCost
        Return If(WeightKg > 2D, 2490D, 1290D)
    End Function

    Public Overrides Function Describe() As String
        Return MyBase.Describe() & $" (szállítás: {ShippingCost():N0} Ft)"
    End Function
End Class

Module OopDemo
    Sub Main()
        Dim items As New List(Of Product) From {New Book("B-1", 5990D, 0.6D), New Book("B-2", 3490D, 2.4D)}
        items.Sort()                                     ' IComparable alapján, ár szerint
        For Each p In items
            Console.WriteLine(p.Describe())
            If TypeOf p Is IShippable Then Console.WriteLine("  → fizikai termék")
        Next
    End Sub
End Module
```

## LINQ és XML literálok
<!-- q: Hogyan használjam a LINQ-t és az XML literálokat VB.NET-ben? -->
<!-- tags: linq, query syntax, xml literals, xelement, aggregate, group by -->

A VB.NET LINQ query szintaxisa gazdagabb a C#-énál (`Aggregate`, `Take While`, `Skip While`, `Distinct` kulcsszóként), és a metódus szintaxis (`.Where(Function(x) ...)`) is elérhető. Egyedi funkció az XML literál: XML-t közvetlenül a kódba írhatsz, `<%= %>` beágyazott kifejezésekkel, és a `.<elem>`, `.@attr`, `...<desc>` tengelyekkel kérdezhetsz le, ami a konfig- és exportfájlok kezelését nagyon tömörré teszi. Buktató: a LINQ itt is késleltetett végrehajtású, és a `From` lekérdezésben a `Group By ... Into` szintaxis eltér a C#-étól.

```vbnet
Option Strict On
Option Infer On

Imports System.Xml.Linq

Module LinqXmlDemo
    Class Sale
        Public Property Region As String
        Public Property Product As String
        Public Property Amount As Decimal
    End Class

    Sub Main()
        Dim sales As New List(Of Sale) From {
            New Sale With {.Region = "Észak", .Product = "Laptop", .Amount = 450000D},
            New Sale With {.Region = "Dél", .Product = "Egér", .Amount = 9000D},
            New Sale With {.Region = "Észak", .Product = "Monitor", .Amount = 120000D}
        }

        ' Query szintaxis csoportosítással
        Dim byRegion = From s In sales
                       Group By s.Region Into Total = Sum(s.Amount), Count = Count()
                       Order By Total Descending

        ' Aggregate kulcsszó: azonnal kiértékelődik
        Dim maxSale = Aggregate s In sales Into Max(s.Amount)

        ' XML literál beágyazott LINQ-kel
        Dim report As XElement =
            <report generated=<%= DateTime.UtcNow.ToString("o") %>>
                <%= From r In byRegion
                    Select <region name=<%= r.Region %> count=<%= r.Count %>>
                               <total><%= r.Total %></total>
                           </region> %>
            </report>

        Console.WriteLine(report)
        Console.WriteLine($"Legnagyobb eladás: {maxSale:N0}")

        ' XML tengelyek: .<gyerek>, .@attribútum, ...<leszármazott>
        Dim northTotal = (From r In report.<region>
                          Where r.@name = "Észak"
                          Select CDec(r.<total>.Value)).FirstOrDefault()
        Console.WriteLine($"Észak összesen: {northTotal:N0}")
        Console.WriteLine($"Régiók száma: {report...<region>.Count()}")
    End Sub
End Module
```

## Async/Await
<!-- q: Hogyan írjak aszinkron kódot Async és Await kulcsszavakkal VB.NET-ben? -->
<!-- tags: async, await, task, httpclient, cancellation, concurrency -->

Az `Async Function ... As Task(Of T)` és az `Await` ugyanazt az állapotgépes mechanizmust használja, mint a C#: várakozás közben a szál felszabadul, a UI nem fagy le. Több független műveletet `Task.WhenAll`-lal futtass párhuzamosan, a lemondáshoz adj tovább `CancellationToken`-t. Buktatók: az `Async Sub` csak eseménykezelő lehet (a kivétele nem kapható el), a `.Result`/`.Wait()` UI-szálon deadlockot okoz, könyvtári kódban pedig használj `ConfigureAwait(False)`-t.

```vbnet
Option Strict On

Imports System.Net.Http
Imports System.Threading

Module AsyncDemo
    ' Egy HttpClient az alkalmazás egész életére (socket-kimerülés ellen)
    Private ReadOnly Http As New HttpClient With {.Timeout = TimeSpan.FromSeconds(10)}

    Async Function GetLengthAsync(url As String, ct As CancellationToken) As Task(Of Integer)
        Try
            Dim body = Await Http.GetStringAsync(url, ct).ConfigureAwait(False)
            Return body.Length
        Catch ex As HttpRequestException
            Console.WriteLine($"{url}: {ex.Message}")
            Return -1
        End Try
    End Function

    Async Function SimulateWorkAsync(id As Integer, ct As CancellationToken) As Task(Of String)
        Await Task.Delay(100 * id, ct)              ' nem blokkol szálat
        Return $"feladat {id} kész"
    End Function

    Async Function RunAsync() As Task
        Using cts As New CancellationTokenSource(TimeSpan.FromSeconds(5))
            ' Párhuzamos indítás, közös várakozás
            Dim tasks = Enumerable.Range(1, 3).Select(Function(i) SimulateWorkAsync(i, cts.Token)).ToArray()
            Dim results = Await Task.WhenAll(tasks)
            Console.WriteLine(String.Join(", ", results))

            ' Hálózati példa (example.com tesztcélra fenntartott domain)
            Dim len = Await GetLengthAsync("https://example.com", cts.Token)
            Console.WriteLine($"Válasz hossza: {len}")
        End Using
    End Function

    Sub Main()
        ' Konzolalkalmazás belépési pontján egyszer szabad blokkolni
        RunAsync().GetAwaiter().GetResult()
    End Sub
End Module
```

## Hibakezelés: Try/Catch When, Finally, Using
<!-- q: Hogyan kezeljem a kivételeket és az erőforrásokat VB.NET-ben? -->
<!-- tags: exceptions, try catch, when filter, finally, using, idisposable, custom exception -->

A strukturált hibakezelés `Try ... Catch ... Finally ... End Try` blokkokkal megy; a `Catch ex As T When feltétel` kivételszűrő a verem visszagörgetése előtt dönt, így a nem kezelt eset eredeti stack trace-e megmarad. A `Using` blokk garantálja a `Dispose` hívását (fájl, adatbázis-kapcsolat) kivétel esetén is. A régi `On Error GoTo` csak VB6-kompatibilitás miatt létezik, ne használd. Újradobáshoz `Throw` (paraméter nélkül) kell, a `Throw ex` elveszíti az eredeti stack trace-t.

```vbnet
Option Strict On

Imports System.IO

' Saját kivételtípus domain-hibához
Public Class ImportException
    Inherits Exception
    Public ReadOnly Property LineNumber As Integer
    Public Sub New(message As String, lineNumber As Integer, inner As Exception)
        MyBase.New(message, inner)
        Me.LineNumber = lineNumber
    End Sub
End Class

Module ErrorDemo
    Function SumCsvColumn(path As String, column As Integer) As Decimal
        Dim total As Decimal = 0D
        Dim lineNo = 0
        ' Using: a reader biztosan bezárul, akkor is, ha kivétel jön
        Using reader As New StreamReader(path)
            Do While Not reader.EndOfStream
                lineNo += 1
                Dim parts = reader.ReadLine().Split(";"c)
                Try
                    total += Decimal.Parse(parts(column), Globalization.CultureInfo.InvariantCulture)
                Catch ex As FormatException
                    Throw New ImportException($"Hibás szám a(z) {lineNo}. sorban", lineNo, ex)
                Catch ex As IndexOutOfRangeException When column > 0
                    ' Kivételszűrő: csak akkor kapjuk el, ha a feltétel igaz
                    Throw New ImportException($"Hiányzó oszlop a(z) {lineNo}. sorban", lineNo, ex)
                End Try
            Loop
        End Using
        Return total
    End Function

    Sub Main()
        ' Saját ideiglenes fájl — meglévő adathoz nem nyúlunk
        Dim tmp = Path.Combine(Path.GetTempPath(), $"vbdemo_{Guid.NewGuid():N}.csv")
        File.WriteAllLines(tmp, {"alma;120.5", "körte;80", "szilva;abc"})
        Try
            Console.WriteLine(SumCsvColumn(tmp, 1))
        Catch ex As ImportException
            Console.WriteLine($"Import hiba ({ex.LineNumber}. sor): {ex.Message} ← {ex.InnerException?.GetType().Name}")
        Finally
            File.Delete(tmp)                 ' takarítás mindenképp
        End Try
    End Sub
End Module
```

## Események és delegate-ek
<!-- q: Hogyan működnek az események VB.NET-ben (WithEvents, Handles, AddHandler)? -->
<!-- tags: events, delegates, withevents, handles, addhandler, raiseevent, lambda -->

A VB.NET-ben az eseményt `Event` deklarálja és `RaiseEvent` váltja ki (ami automatikusan ellenőrzi, van-e feliratkozó). Feliratkozni deklaratívan lehet (`WithEvents` mező + `Handles` a kezelőn — ezt használja a WinForms tervező), vagy dinamikusan `AddHandler`/`RemoveHandler`-rel, ami lambdával is működik. A delegate típus `Delegate Function`/`Sub`, de a beépített `Func(Of ...)` és `Action(Of ...)` általában elég. Buktató: a dinamikusan felvett kezelőt le kell iratkoztatni, különben a hosszú életű objektum memóriában tartja a feliratkozót.

```vbnet
Option Strict On

Public Class TemperatureSensor
    ' Esemény szabványos (sender, e) szignatúrával
    Public Event ThresholdExceeded As EventHandler(Of TemperatureEventArgs)
    Public Property Threshold As Double = 30.0

    Public Sub Report(value As Double)
        If value > Threshold Then
            RaiseEvent ThresholdExceeded(Me, New TemperatureEventArgs(value))   ' null-ellenőrzés automatikus
        End If
    End Sub
End Class

Public Class TemperatureEventArgs
    Inherits EventArgs
    Public ReadOnly Property Value As Double
    Public Sub New(value As Double)
        Me.Value = value
    End Sub
End Class

Public Class AlarmPanel
    ' Deklaratív feliratkozás: WithEvents + Handles
    Private WithEvents _sensor As TemperatureSensor

    Public Sub New(sensor As TemperatureSensor)
        _sensor = sensor
    End Sub

    Private Sub OnHot(sender As Object, e As TemperatureEventArgs) Handles _sensor.ThresholdExceeded
        Console.WriteLine($"[Panel] Riasztás: {e.Value:F1} °C")
    End Sub
End Class

Module EventDemo
    Sub Main()
        Dim sensor As New TemperatureSensor()
        Dim panel As New AlarmPanel(sensor)

        ' Dinamikus feliratkozás lambdával — eltároljuk a leiratkozáshoz
        Dim logger As EventHandler(Of TemperatureEventArgs) =
            Sub(s, e) Console.WriteLine($"[Log] {DateTime.Now:HH:mm:ss} {e.Value}")
        AddHandler sensor.ThresholdExceeded, logger

        ' Func delegate: átalakító függvény paraméterként
        Dim fahrenheitToCelsius As Func(Of Double, Double) = Function(f) (f - 32) * 5 / 9
        For Each f In {68.0, 95.0, 104.0}
            sensor.Report(fahrenheitToCelsius(f))
        Next

        RemoveHandler sensor.ThresholdExceeded, logger   ' leiratkozás
        sensor.Report(45)                                 ' már csak a panel reagál
    End Sub
End Module
```

## Generikusok és gyűjtemények
<!-- q: Hogyan használjam a generikus típusokat és gyűjteményeket VB.NET-ben? -->
<!-- tags: generics, of t, constraints, dictionary, list, collections, hashset -->

A generikus típusparaméter VB.NET-ben `(Of T)`, a megszorítások `As` után jönnek: `(Of T As {Class, IComparable(Of T), New})`. A `List(Of T)`, `Dictionary(Of TKey, TValue)`, `HashSet(Of T)` és `Queue(Of T)` a mindennapi alapgyűjtemények; a gyűjtemény-inicializáló a `From { ... }` szintaxis. Kerüld a régi, nem generikus `ArrayList`-et és a VB6-ból maradt `Collection` osztályt, mert boxingot és futásidejű típushibákat okoznak. Szótárnál a `TryGetValue` gyorsabb és biztonságosabb, mint a `ContainsKey` + indexelés.

```vbnet
Option Strict On
Option Infer On

' Generikus LRU cache megszorítással
Public Class LruCache(Of TKey As IEquatable(Of TKey), TValue)
    Private ReadOnly _capacity As Integer
    Private ReadOnly _map As New Dictionary(Of TKey, LinkedListNode(Of KeyValuePair(Of TKey, TValue)))
    Private ReadOnly _order As New LinkedList(Of KeyValuePair(Of TKey, TValue))

    Public Sub New(capacity As Integer)
        If capacity <= 0 Then Throw New ArgumentOutOfRangeException(NameOf(capacity))
        _capacity = capacity
    End Sub

    Public Function TryGet(key As TKey, ByRef value As TValue) As Boolean
        Dim node As LinkedListNode(Of KeyValuePair(Of TKey, TValue)) = Nothing
        If Not _map.TryGetValue(key, node) Then Return False
        _order.Remove(node)                  ' legutóbb használt → a lista elejére
        _order.AddFirst(node)
        value = node.Value.Value
        Return True
    End Function

    Public Sub Put(key As TKey, value As TValue)
        Dim existing As LinkedListNode(Of KeyValuePair(Of TKey, TValue)) = Nothing
        If _map.TryGetValue(key, existing) Then _order.Remove(existing)
        If _map.Count >= _capacity AndAlso existing Is Nothing Then
            Dim lru = _order.Last            ' a legrégebben használt kiesik
            _order.RemoveLast()
            _map.Remove(lru.Value.Key)
        End If
        _map(key) = _order.AddFirst(New KeyValuePair(Of TKey, TValue)(key, value))
    End Sub
End Class

Module GenericsDemo
    ' Generikus metódus: legnagyobb elem bármilyen összehasonlítható típusra
    Function MaxOf(Of T As IComparable(Of T))(items As IEnumerable(Of T)) As T
        Return items.Aggregate(Function(a, b) If(a.CompareTo(b) >= 0, a, b))
    End Function

    Sub Main()
        Dim cache As New LruCache(Of String, Integer)(2)
        cache.Put("a", 1) : cache.Put("b", 2)
        Dim v As Integer
        cache.TryGet("a", v)                 ' "a" frissen használt lesz
        cache.Put("c", 3)                    ' "b" esik ki
        Console.WriteLine($"b benne van? {cache.TryGet("b", v)}")   ' False

        Dim tags As New HashSet(Of String)(StringComparer.OrdinalIgnoreCase) From {"VB", "vb", "Net"}
        Console.WriteLine($"{tags.Count} egyedi címke, max: {MaxOf(New List(Of Integer) From {3, 9, 4})}")
    End Sub
End Module
```

## Modulok, extension methodok és Select Case
<!-- q: Mire jók a Module-ok, az extension methodok és a Select Case VB.NET-ben? -->
<!-- tags: module, extension methods, select case, string interpolation, with block -->

A `Module` statikus tagok tárolója (C#-ban `static class`), a tagjai névtérszinten, minősítés nélkül elérhetők; extension methodot csak modulban, `<Extension>` attribútummal definiálhatsz. A `Select Case` erősebb a C# klasszikus switch-énél: tartományokat (`1 To 5`), relációkat (`Is > 100`) és listákat is kezel, a `With` blokk pedig ismételt objektum-hivatkozást spórol meg. Buktató: a modul tagjai globálisan látszanak, ami névütközéshez vezethet, és a `Select Case` stringeknél alapból kis-nagybetű érzékeny (`Option Compare Binary`).

```vbnet
Option Strict On

Imports System.Runtime.CompilerServices
Imports System.Text

Public Module StringExtensions
    ' Extension method: úgy hívható, mintha a String saját metódusa lenne
    <Extension>
    Public Function Truncate(value As String, maxLength As Integer, Optional suffix As String = "…") As String
        If value Is Nothing OrElse value.Length <= maxLength Then Return value
        Return value.Substring(0, Math.Max(0, maxLength - suffix.Length)) & suffix
    End Function

    <Extension>
    Public Function ToSlug(value As String) As String
        Dim sb As New StringBuilder()
        For Each ch In value.Normalize(NormalizationForm.FormD).ToLowerInvariant()
            Select Case Char.GetUnicodeCategory(ch)
                Case Globalization.UnicodeCategory.NonSpacingMark
                    ' ékezetek elhagyása (á → a)
                Case Else
                    sb.Append(If(Char.IsLetterOrDigit(ch), ch, "-"c))
            End Select
        Next
        Return sb.ToString().Trim("-"c)
    End Function
End Module

Module SelectCaseDemo
    Function Grade(points As Integer) As String
        Select Case points
            Case Is < 0, Is > 100 : Return "érvénytelen"
            Case 90 To 100 : Return "jeles"
            Case 75 To 89 : Return "jó"
            Case 60 To 74 : Return "közepes"
            Case 50 To 59 : Return "elégséges"
            Case Else : Return "elégtelen"
        End Select
    End Function

    Sub Main()
        Console.WriteLine("Árvíztűrő tükörfúrógép".ToSlug())          ' arvizturo-tukorfurogep
        Console.WriteLine("Nagyon hosszú termékleírás".Truncate(12))
        For Each p In {95, 80, 55, 120}
            Console.WriteLine($"{p} pont → {Grade(p)}")
        Next

        ' With blokk: ismételt objektum-hivatkozás nélkül
        Dim sb As New StringBuilder()
        With sb
            .Append("Összesítés: ")
            .Append(Grade(77))
            .AppendLine()
        End With
        Console.Write(sb.ToString())
    End Sub
End Module
```

## WinForms alkalmazás
<!-- q: Hogyan építsek WinForms ablakot VB.NET-ben, reszponzív UI-val? -->
<!-- tags: winforms, windows forms, gui, async ui, data binding, desktop -->

A WinForms a VB.NET klasszikus terepe: a tervező a vezérlőket `WithEvents` mezőkként generálja, a kezelők `Handles`-szel kötődnek. A hosszú műveleteket `Async Sub` eseménykezelőben `Await`-tel futtasd, így az UI-szál nem fagy le, és az `Await` után automatikusan az UI-szálon folytatódik (a vezérlők biztonságosan módosíthatók). Háttérszálról közvetlenül vezérlőhöz nyúlni tilos (`InvalidOperationException`), ilyenkor `Invoke` vagy `IProgress(Of T)` kell. A `BindingSource` + `BindingList(Of T)` adatkötést ad a gridhez.

```vbnet
Option Strict On

Imports System.ComponentModel
Imports System.Windows.Forms

Public Class MainForm
    Inherits Form

    Private WithEvents btnStart As New Button With {.Text = "Feldolgozás", .Dock = DockStyle.Top, .Height = 36}
    Private ReadOnly progressBar As New ProgressBar With {.Dock = DockStyle.Top}
    Private ReadOnly grid As New DataGridView With {.Dock = DockStyle.Fill, .ReadOnly = True}
    Private ReadOnly rows As New BindingList(Of ResultRow)()

    Public Sub New()
        Text = "Feldolgozó"
        Width = 480 : Height = 360
        grid.DataSource = New BindingSource With {.DataSource = rows}   ' adatkötés
        Controls.AddRange({grid, progressBar, btnStart})               ' Dock sorrend: fordított
    End Sub

    ' Async Sub CSAK eseménykezelőben elfogadható
    Private Async Sub btnStart_Click(sender As Object, e As EventArgs) Handles btnStart.Click
        btnStart.Enabled = False
        rows.Clear()
        ' IProgress: a háttérből jövő jelentés az UI-szálon fut le
        Dim progress As New Progress(Of Integer)(Sub(p) progressBar.Value = p)
        Try
            Dim results = Await Task.Run(Function() Compute(progress))   ' CPU-munka háttérszálon
            For Each r In results
                rows.Add(r)                     ' Await után ismét az UI-szálon vagyunk
            Next
        Catch ex As Exception
            MessageBox.Show(ex.Message, "Hiba", MessageBoxButtons.OK, MessageBoxIcon.Error)
        Finally
            btnStart.Enabled = True
        End Try
    End Sub

    Private Shared Function Compute(progress As IProgress(Of Integer)) As List(Of ResultRow)
        Dim list As New List(Of ResultRow)()
        For i = 1 To 10
            Threading.Thread.Sleep(100)        ' szimulált munka (háttérszálon szabad)
            list.Add(New ResultRow With {.Id = i, .Square = i * i})
            progress.Report(i * 10)
        Next
        Return list
    End Function
End Class

Public Class ResultRow
    Public Property Id As Integer
    Public Property Square As Integer
End Class

Module Program
    <STAThread>
    Sub Main()
        Application.EnableVisualStyles()
        Application.Run(New MainForm())
    End Sub
End Module
```

## VBA: Excel makrók
<!-- q: Hogyan írjak hatékony és biztonságos VBA makrót Excelhez? -->
<!-- tags: vba, excel, macro, office automation, range, arrays, error handling -->

A VBA az Office alkalmazásokba épített, VB6-alapú nyelv (nem .NET): `Sub`/`Function` eljárásokkal, `Dim` deklarációval, és az Office objektummodellel (Workbook, Worksheet, Range) dolgozik. Mindig használj `Option Explicit`-et, a sebességhez olvasd be a tartományt egyszerre tömbbe (`Range.Value`), dolgozd fel memóriában, és egyben írd vissza — a cellánkénti írás nagyon lassú; közben kapcsold ki a `ScreenUpdating`-et és az automatikus számolást. A hibakezelés `On Error GoTo` címkével megy, ahol a kilépési ágban vissza kell állítani az alkalmazásbeállításokat. Biztonság: csak megbízható forrásból engedélyezz makrót, és a makró ne töröljön/írjon felül adatot megerősítés nélkül.

```vba
Option Explicit

' Régiónkénti összesítés új munkalapra — a forrásadatot NEM módosítja
' Elvárt forrás: aktív lap, A oszlop = régió, B oszlop = összeg, 1. sor fejléc
Public Sub SummarizeByRegion()
    Dim src As Worksheet, dst As Worksheet
    Dim data As Variant, result() As Variant
    Dim totals As Object, key As Variant
    Dim lastRow As Long, i As Long, r As Long

    On Error GoTo ErrHandler
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual

    Set src = ActiveSheet
    lastRow = src.Cells(src.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then
        MsgBox "Nincs feldolgozható adat.", vbExclamation
        GoTo CleanUp
    End If

    ' Egyetlen olvasás tömbbe — sokkal gyorsabb, mint cellánként
    data = src.Range("A2:B" & lastRow).Value
    Set totals = CreateObject("Scripting.Dictionary")

    For i = 1 To UBound(data, 1)
        If IsNumeric(data(i, 2)) And Len(data(i, 1)) > 0 Then
            totals(CStr(data(i, 1))) = totals(CStr(data(i, 1))) + CDbl(data(i, 2))
        End If
    Next i

    ' Eredmény tömbbe, majd egyetlen írás egy ÚJ munkalapra
    ReDim result(1 To totals.Count + 1, 1 To 2)
    result(1, 1) = "Régió": result(1, 2) = "Összesen"
    r = 2
    For Each key In totals.Keys
        result(r, 1) = key
        result(r, 2) = totals(key)
        r = r + 1
    Next key

    Set dst = ThisWorkbook.Worksheets.Add(After:=src)
    dst.Range("A1").Resize(UBound(result, 1), 2).Value = result
    dst.Columns("A:B").AutoFit

CleanUp:
    ' Az alkalmazásbeállításokat MINDIG visszaállítjuk
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    Exit Sub

ErrHandler:
    MsgBox "Hiba " & Err.Number & ": " & Err.Description, vbCritical
    Resume CleanUp
End Sub
```
